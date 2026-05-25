CREATE TABLE IF NOT EXISTS video_benchmark_items (
    id BIGSERIAL PRIMARY KEY,
    shot_type TEXT NOT NULL DEFAULT '',
    task_type TEXT NOT NULL DEFAULT '',
    question_type TEXT NOT NULL DEFAULT '',
    scene TEXT NOT NULL DEFAULT '',
    screen_size TEXT NOT NULL DEFAULT '',
    character_image_asset TEXT NOT NULL DEFAULT '',
    scene_image_asset TEXT NOT NULL DEFAULT '',
    prop_image_asset TEXT NOT NULL DEFAULT '',
    audio_input TEXT NOT NULL DEFAULT '',
    video_input TEXT NOT NULL DEFAULT '',
    text_prompt TEXT NOT NULL DEFAULT '',
    video_output TEXT NOT NULL DEFAULT '',
    score SMALLINT CHECK (score IS NULL OR score BETWEEN 0 AND 5),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE video_benchmark_items IS '视频 benchmark 题目与输出评分表';
COMMENT ON COLUMN video_benchmark_items.id IS 'ID';
COMMENT ON COLUMN video_benchmark_items.shot_type IS '镜头类型';
COMMENT ON COLUMN video_benchmark_items.task_type IS '任务类型';
COMMENT ON COLUMN video_benchmark_items.question_type IS '题目类型';
COMMENT ON COLUMN video_benchmark_items.scene IS '场景';
COMMENT ON COLUMN video_benchmark_items.screen_size IS '屏幕尺寸';
COMMENT ON COLUMN video_benchmark_items.character_image_asset IS '人物图片素材';
COMMENT ON COLUMN video_benchmark_items.scene_image_asset IS '场景图片素材';
COMMENT ON COLUMN video_benchmark_items.prop_image_asset IS '道具图片素材';
COMMENT ON COLUMN video_benchmark_items.audio_input IS '音频输入';
COMMENT ON COLUMN video_benchmark_items.video_input IS '视频输入';
COMMENT ON COLUMN video_benchmark_items.text_prompt IS '文字提示词';
COMMENT ON COLUMN video_benchmark_items.video_output IS '视频输出';
COMMENT ON COLUMN video_benchmark_items.score IS 'Score（0-5分）';

CREATE INDEX IF NOT EXISTS idx_video_benchmark_items_task_type
    ON video_benchmark_items(task_type);

CREATE INDEX IF NOT EXISTS idx_video_benchmark_items_question_type
    ON video_benchmark_items(question_type);

CREATE INDEX IF NOT EXISTS idx_video_benchmark_items_shot_type
    ON video_benchmark_items(shot_type);

CREATE INDEX IF NOT EXISTS idx_video_benchmark_items_score
    ON video_benchmark_items(score);
