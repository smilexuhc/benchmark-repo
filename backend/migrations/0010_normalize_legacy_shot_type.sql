-- 把 legacy shot_type 值规范化到新枚举上。
-- 旧值 → 新值：
--   单个镜头 / 单个 → 单镜头
--   多镜头 / 连续镜头 → 连续镜头 2*15s
UPDATE video_benchmark_items
   SET shot_type = '单镜头'
 WHERE shot_type IN ('单个镜头', '单个');

UPDATE video_benchmark_items
   SET shot_type = '连续镜头 2*15s'
 WHERE shot_type IN ('多镜头', '连续镜头');
