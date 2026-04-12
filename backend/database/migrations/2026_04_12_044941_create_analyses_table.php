<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('analyses', function (Blueprint $table) {
            $table->id();

            $table->foreignId('user_id')
                  ->constrained()
                  ->cascadeOnDelete();

            $table->string('doc_name');
            $table->enum('doc_type', ['essay', 'research', 'bizplan']);

            $table->text('file_path');

            $table->enum('status', ['pending', 'processing', 'done', 'failed'])
                  ->default('pending');

            $table->string('task_id')->unique()->nullable();

            $table->json('result_json')->nullable();

            $table->decimal('score_overall', 4, 2)->nullable();

            $table->text('error_message')->nullable();

            $table->timestamp('completed_at')->nullable();

            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('analyses');
    }
};