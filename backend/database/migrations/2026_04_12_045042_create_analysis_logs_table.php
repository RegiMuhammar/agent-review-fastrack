<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('analysis_logs', function (Blueprint $table) {
            $table->id();

            $table->foreignId('analysis_id')
                  ->constrained('analyses')
                  ->cascadeOnDelete();

            $table->string('step', 50);

            $table->enum('status', ['pending', 'processing', 'done', 'failed']);

            $table->text('message')->nullable();

            $table->json('metadata_json')->nullable();

            $table->timestamp('created_at')->useCurrent();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('analysis_logs');
    }
};
