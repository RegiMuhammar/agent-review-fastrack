<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::table('analyses', function (Blueprint $table) {
            $table->string('access_code_hash', 64)->nullable()->after('task_id')->index();
            $table->timestamp('access_code_sent_at')->nullable()->after('access_code_hash');
        });
    }

    public function down(): void
    {
        Schema::table('analyses', function (Blueprint $table) {
            $table->dropColumn(['access_code_hash', 'access_code_sent_at']);
        });
    }
};
