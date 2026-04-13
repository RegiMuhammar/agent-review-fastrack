<?php

namespace App\Http\Controllers;

use App\Models\Analysis;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;
use Illuminate\Validation\Rule;
use Symfony\Component\HttpFoundation\BinaryFileResponse;

class AnalysisController extends Controller
{
    public function index(Request $request): JsonResponse
    {
        $analyses = Analysis::query()
            ->where('user_id', $request->user()->id)
            ->latest()
            ->get();

        return response()->json([
            'success' => true,
            'message' => 'Daftar dokumen analisis berhasil diambil.',
            'data' => [
                'analyses' => $analyses,
            ],
        ]);
    }

    public function store(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'doc_name' => ['required', 'string', 'max:255'],
            'doc_type' => ['required', Rule::in(['essay', 'research', 'bizplan'])],
            'file' => [
                'bail',
                'required',
                'file',
                'mimetypes:application/pdf',
                function (string $attribute, mixed $value, \Closure $fail): void {
                    if (! $value instanceof \Illuminate\Http\UploadedFile) {
                        $fail('File tidak valid.');

                        return;
                    }

                    $maxSizeBytes = 10 * 1024 * 1024;
                    $isTooLarge = $value->getSize() > $maxSizeBytes;

                    $pages = $this->countPdfPages($value->getPathname());

                    if ($pages === null) {
                        $fail('PDF tidak valid atau tidak dapat dibaca.');

                        return;
                    }

                    $isTooManyPages = $pages > 15;

                    if ($isTooLarge && $isTooManyPages) {
                        $fail('Ukuran file maksimal 10MB dan maksimal 15 halaman');

                        return;
                    }

                    if ($isTooLarge) {
                        $fail('Ukuran file maksimal 10MB.');

                        return;
                    }

                    if ($isTooManyPages) {
                        $fail('Jumlah halaman PDF maksimal 15 halaman.');
                    }
                },
            ],
        ], [
            'file.mimetypes' => 'File harus berformat PDF.',
        ]);

        $user = $request->user();
        $storedPath = $validated['file']->store('analyses/'.$user->id, 'local');

        $analysis = Analysis::create([
            'user_id' => $user->id,
            'doc_name' => $validated['doc_name'],
            'doc_type' => $validated['doc_type'],
            'file_path' => $storedPath,
            'status' => 'pending',
        ]);

        return response()->json([
            'success' => true,
            'message' => 'Dokumen berhasil diunggah untuk analisis.',
            'data' => [
                'analysis' => $analysis,
                'file_path' => $analysis->file_path,
            ],
        ], 201);
    }

    public function show(Request $request, int $analysis): JsonResponse
    {
        $analysisData = Analysis::query()
            ->where('user_id', $request->user()->id)
            ->whereKey($analysis)
            ->firstOrFail();

        return response()->json([
            'success' => true,
            'message' => 'Detail dokumen analisis berhasil diambil.',
            'data' => [
                'analysis' => $analysisData,
            ],
        ]);
    }

    public function file(Request $request, int $analysis): BinaryFileResponse
    {
        $analysisData = Analysis::query()
            ->where('user_id', $request->user()->id)
            ->whereKey($analysis)
            ->firstOrFail();

        abort_unless(
            Storage::disk('local')->exists($analysisData->file_path),
            404,
            'File dokumen tidak ditemukan.'
        );

        return response()->file(
            Storage::disk('local')->path($analysisData->file_path),
            [
                'Content-Type' => 'application/pdf',
                'Content-Disposition' => 'inline; filename="'.basename($analysisData->file_path).'"',
            ]
        );
    }

    public function destroy(Request $request, int $analysis): JsonResponse
    {
        $analysisData = Analysis::query()
            ->where('user_id', $request->user()->id)
            ->whereKey($analysis)
            ->firstOrFail();

        if (! empty($analysisData->file_path)) {
            Storage::disk('local')->delete($analysisData->file_path);
        }

        $analysisData->delete();

        return response()->json([
            'success' => true,
            'message' => 'Data analisis berhasil dihapus.',
        ]);
    }

    private function countPdfPages(string $path): ?int
    {
        $content = @file_get_contents($path);

        if ($content === false || $content === '') {
            return null;
        }

        preg_match_all('/\/Type\s*\/Page\b/', $content, $matches);
        $count = count($matches[0] ?? []);

        return $count > 0 ? $count : null;
    }
}
