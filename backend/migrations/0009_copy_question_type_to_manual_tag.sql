-- 把存量行的 question_type 文本复制到 manual_tag；
-- 只填充 manual_tag 为空的行，避免重复迁移；question_type 原值保留不动。
UPDATE video_benchmark_items
   SET manual_tag = question_type
 WHERE manual_tag = ''
   AND question_type <> '';
