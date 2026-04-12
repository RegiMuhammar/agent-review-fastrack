<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('feedbacks', function (Blueprint $table) {
            $table->id();

            $table->foreignId('analysis_id')
                  ->constrained('analyses')
                  ->cascadeOnDelete();

            $table->foreignId('user_id')
                  ->constrained()
                  ->cascadeOnDelete();

            $table->unsignedTinyInteger('rating');

            $table->text('comment')->nullable();

            $table->timestamp('created_at')->useCurrent();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('feedbacks');
    }
};