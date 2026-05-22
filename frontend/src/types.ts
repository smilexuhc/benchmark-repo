export interface CharImage {
  id: number
  filename: string
  source: string
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

/** 筛选维度：字段名 -> 选中值数组 */
export type Filters = Record<string, string[]>

export type Options = Record<string, string[]>

export const CHARACTER_FILTER_FIELDS = ['era', 'type', 'gender', 'age', 'genre']
export const SCENE_FILTER_FIELDS = ['era', 'scene_type', 'genre', 'mood']

export const FIELD_LABELS: Record<string, string> = {
  era: '时代',
  type: '类型',
  gender: '性别',
  age: '年龄段',
  genre: '常见题材',
  scene_type: '场景类型',
  mood: '氛围时段',
}

export const emptyCharacter: CharacterInput = {
  era: '', type: '', gender: '', age: '', persona: '',
  body: '', features: '', genre: '', prompt: '', description: '',
}

export const emptyScene: SceneInput = {
  name: '', era: '', scene_type: '', genre: '', mood: '',
  elements: '', prompt: '', description: '',
}
