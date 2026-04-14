<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

#[Fillable([
    'analysis_id',
    'user_id',
    'rating',
    'comment',
])]
class Feedback extends Model
{
    protected $table = 'feedbacks';

    public const UPDATED_AT = null;

    protected function casts(): array
    {
        return [
            'rating' => 'integer',
        ];
    }

    public function analysis(): BelongsTo
    {
        return $this->belongsTo(Analysis::class);
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }
}
