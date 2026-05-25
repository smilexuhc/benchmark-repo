export interface CharImage {
  id: number
  filename: string
  source: string
  media_type?: string
  created_at: string
}

export interface MediaAsset {
  id: number
  asset_id: number
  asset_kind: 'character' | 'scene' | 'audio' | 'prop'
  object_key: string
  filename: string
  title: string
  subtitle: string
  source: string
  media_type: 'image' | 'audio'
  url: string
  thumbnail_url: string
  created_at: string
}

/** 角色与场景共有的基础结构（供通用组件使用） */
export interface AssetBase {
  id: number
  prompt: string
  cover_image_id: number | null
  cover_filename: string | null
  images: CharImage[]
}

export interface Character extends AssetBase {
  era: string
  type: string
  gender: string
  age: string
  persona: string
  body: string
  features: string
  genre: string
  description: string
  created_at: string
  updated_at: string
}

export type SceneViewKind = 'reverse' | 'multiview'

export interface Scene extends AssetBase {
  name: string
  era: string
  scene_type: string
  genre: string
  mood: string
  elements: string
  description: string
  views: Record<SceneViewKind, CharImage | null>
  created_at: string
  updated_at: string
}

export type CharacterInput = Pick<
  Character,
  | 'era' | 'type' | 'gender' | 'age' | 'persona'
  | 'body' | 'features' | 'genre' | 'prompt' | 'description'
>

export type SceneInput = Pick<
  Scene,
  'name' | 'era' | 'scene_type' | 'genre' | 'mood' | 'elements' | 'prompt' | 'description'
>

export interface VideoBenchmarkItem {
  id: number
  shot_type: string
  task_type: string
  question_type: string
  scene: string
  screen_size: string
  character_image_asset: string
  scene_image_asset: string
  prop_image_asset: string
  audio_input: string
  video_input: string
  text_prompt: string
  judging_criteria: string
  video_output: string
  score: number | null
  character_image_id: number | null
  scene_image_id: number | null
  prop_image_id: number | null
  audio_input_id: number | null
  character_image_ids: number[]
  scene_image_ids: number[]
  prop_image_ids: number[]
  audio_input_media_ids: number[]
  character_image: MediaAsset | null
  scene_image: MediaAsset | null
  prop_image: MediaAsset | null
  audio_input_media: MediaAsset | null
  character_image_media: MediaAsset[]
  scene_image_media: MediaAsset[]
  prop_image_media: MediaAsset[]
  audio_input_media_items: MediaAsset[]
  created_at: string
  updated_at: string
}

export type VideoBenchmarkItemInput = Pick<
  VideoBenchmarkItem,
  | 'shot_type' | 'task_type' | 'question_type' | 'scene' | 'screen_size'
  | 'character_image_asset' | 'scene_image_asset' | 'prop_image_asset'
  | 'audio_input' | 'video_input' | 'text_prompt' | 'judging_criteria' | 'video_output' | 'score'
  | 'character_image_id' | 'scene_image_id' | 'prop_image_id' | 'audio_input_id'
  | 'character_image_ids' | 'scene_image_ids' | 'prop_image_ids' | 'audio_input_media_ids'
>

export interface MediaAssetListResponse {
  items: MediaAsset[]
  total: number
  limit: number
  offset: number
}

export interface MediaAssetListParams {
  media_type?: 'image' | 'audio'
  asset_kind?: 'character' | 'scene' | 'audio' | 'prop'
  q?: string
  limit?: number
  offset?: number
}

export interface VideoBenchmarkListResponse {
  items: VideoBenchmarkItem[]
  total: number
  limit: number
  offset: number
}

export interface VideoBenchmarkListParams {
  limit: number
  offset: number
  q?: string
  shot_type?: string
  task_type?: string
  question_type?: string
  scene?: string
  screen_size?: string
  score?: number | null
}

/** 筛选维度：字段名 -> 选中值数组 */
export type Filters = Record<string, string[]>

export type Options = Record<string, string[]>

export const CHARACTER_FILTER_FIELDS = ['era', 'type', 'gender', 'age', 'genre']
export const SCENE_FILTER_FIELDS = ['era', 'scene_type', 'genre', 'mood']
export const VIDEO_BENCHMARK_FILTER_FIELDS = [
  'shot_type',
  'task_type',
  'question_type',
  'scene',
  'screen_size',
  'score',
] as const

export const FIELD_LABELS: Record<string, string> = {
  era: '时代',
  type: '类型',
  gender: '性别',
  age: '年龄段',
  genre: '常见题材',
  scene_type: '场景类型',
  mood: '氛围时段',
  shot_type: '镜头类型',
  task_type: '任务类型',
  question_type: '题目类型',
  scene: '场景',
  screen_size: '屏幕尺寸',
  character_image_asset: '人物图片素材',
  scene_image_asset: '场景图片素材',
  prop_image_asset: '道具图片素材',
  audio_input: '音频输入',
  character_image_id: '人物图片素材',
  scene_image_id: '场景图片素材',
  prop_image_id: '道具图片素材',
  audio_input_id: '音频输入',
  video_input: '视频输入',
  text_prompt: '文字提示词',
  judging_criteria: '评判标准',
  video_output: '视频输出',
  score: 'Score（0-5分）',
}

export const emptyCharacter: CharacterInput = {
  era: '', type: '', gender: '', age: '', persona: '',
  body: '', features: '', genre: '', prompt: '', description: '',
}

export const emptyScene: SceneInput = {
  name: '', era: '', scene_type: '', genre: '', mood: '',
  elements: '', prompt: '', description: '',
}

export const emptyVideoBenchmarkItem: VideoBenchmarkItemInput = {
  shot_type: '',
  task_type: '',
  question_type: '',
  scene: '',
  screen_size: '',
  character_image_asset: '',
  scene_image_asset: '',
  prop_image_asset: '',
  audio_input: '',
  video_input: '',
  text_prompt: '',
  judging_criteria: '',
  video_output: '',
  score: null,
  character_image_id: null,
  scene_image_id: null,
  prop_image_id: null,
  audio_input_id: null,
  character_image_ids: [],
  scene_image_ids: [],
  prop_image_ids: [],
  audio_input_media_ids: [],
}
