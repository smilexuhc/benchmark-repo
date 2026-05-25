import type {
  Character, CharacterInput, Scene, SceneInput, SceneViewKind,
  CharImage, Filters, MediaAsset, MediaAssetListParams, MediaAssetListResponse, Options,
  VideoBenchmarkItem, VideoBenchmarkItemInput, VideoBenchmarkListParams,
  VideoBenchmarkListResponse,
} from './types'

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    let msg = `请求失败 (${res.status})`
    try {
      const body = await res.json()
      if (body?.detail) msg = body.detail
    } catch {
      /* 忽略解析失败 */
    }
    throw new Error(msg)
  }
  return res.json() as Promise<T>
}

const json = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

interface ApiConfig {
  base: string // /api/characters | /api/scenes
  optionsPath: string
  promptPath: string
  extractPath: string
  exportPath: string
  imageDeletePath: (imgId: number) => string
}

function filterQuery(filters: Filters, q: string): string {
  const params = new URLSearchParams()
  Object.keys(filters).forEach((k) => {
    if (filters[k].length) params.set(k, filters[k].join(','))
  })
  if (q.trim()) params.set('q', q.trim())
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

function queryString(params: object): string {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    qs.set(key, String(value))
  })
  const out = qs.toString()
  return out ? `?${out}` : ''
}

/** 角色与场景共用的资产 API（增删改查 / AI / 图片） */
export interface AssetApi<T, I> {
  options: () => Promise<Options>
  list: (filters: Filters, q: string) => Promise<T[]>
  get: (id: number) => Promise<T>
  create: (data: I) => Promise<T>
  update: (id: number, data: I) => Promise<T>
  remove: (id: number) => Promise<{ ok: boolean }>
  generatePrompt: (data: I) => Promise<{ prompt: string }>
  extractFields: (description: string) => Promise<Partial<I>>
  generateImage: (id: number, prompt: string, setCover?: boolean) => Promise<CharImage>
  uploadImage: (id: number, file: File) => Promise<CharImage>
  deleteImage: (imgId: number) => Promise<{ ok: boolean }>
  setCover: (id: number, imgId: number) => Promise<T>
  exportUrl: (filters: Filters, q: string) => string
}

function makeApi<T, I>(cfg: ApiConfig): AssetApi<T, I> {
  return {
    options: () => req<Options>(cfg.optionsPath),

    list: (filters, q) => req<T[]>(`${cfg.base}${filterQuery(filters, q)}`),

    get: (id) => req<T>(`${cfg.base}/${id}`),
    create: (data) => req<T>(cfg.base, json(data)),
    update: (id, data) => req<T>(`${cfg.base}/${id}`, { ...json(data), method: 'PUT' }),
    remove: (id) => req<{ ok: boolean }>(`${cfg.base}/${id}`, { method: 'DELETE' }),

    generatePrompt: (data) =>
      req<{ prompt: string }>(cfg.promptPath, json(data)),

    extractFields: (description) =>
      req<Partial<I>>(cfg.extractPath, json({ description })),

    generateImage: (id, prompt, setCover = false) =>
      req<CharImage>(
        `${cfg.base}/${id}/generate-image`,
        json({ prompt, set_cover: setCover }),
      ),

    uploadImage: (id, file) => {
      const fd = new FormData()
      fd.append('file', file)
      return req<CharImage>(`${cfg.base}/${id}/images`, { method: 'POST', body: fd })
    },

    deleteImage: (imgId) =>
      req<{ ok: boolean }>(cfg.imageDeletePath(imgId), { method: 'DELETE' }),

    setCover: (id, imgId) =>
      req<T>(`${cfg.base}/${id}/cover/${imgId}`, { method: 'PUT' }),

    exportUrl: (filters, q) => `${cfg.exportPath}${filterQuery(filters, q)}`,
  }
}

export const characterApi: AssetApi<Character, CharacterInput> = makeApi({
  base: '/api/characters',
  optionsPath: '/api/options',
  promptPath: '/api/generate-prompt',
  extractPath: '/api/extract-fields',
  exportPath: '/api/export/characters',
  imageDeletePath: (id) => `/api/images/${id}`,
})

export const sceneApi = {
  ...makeApi<Scene, SceneInput>({
    base: '/api/scenes',
    optionsPath: '/api/scenes/options',
    promptPath: '/api/scenes/generate-prompt',
    extractPath: '/api/scenes/extract-fields',
    exportPath: '/api/export/scenes',
    imageDeletePath: (id) => `/api/scene-images/${id}`,
  }),
  /** 图生图：以场景封面图为参考，生成正反打 / 4视图 */
  generateView: (id: number, view: SceneViewKind) =>
    req<CharImage>(`/api/scenes/${id}/generate-view`, json({ view })),
}

export const videoBenchmarkApi = {
  list: (params: VideoBenchmarkListParams) =>
    req<VideoBenchmarkListResponse>(
      `/api/video-benchmark-items${queryString(params)}`,
    ),
  get: (id: number) => req<VideoBenchmarkItem>(`/api/video-benchmark-items/${id}`),
  create: (data: VideoBenchmarkItemInput) =>
    req<VideoBenchmarkItem>('/api/video-benchmark-items', json(data)),
  update: (id: number, data: VideoBenchmarkItemInput) =>
    req<VideoBenchmarkItem>(
      `/api/video-benchmark-items/${id}`,
      { ...json(data), method: 'PUT' },
    ),
}

export const mediaAssetsApi = {
  list: (params: MediaAssetListParams) =>
    req<MediaAssetListResponse>(`/api/media-assets${queryString(params)}`),
  upload: (params: MediaAssetListParams, file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    const query = queryString({
      media_type: params.media_type,
      asset_kind: params.asset_kind,
      title: file.name,
    })
    return req<MediaAsset>(`/api/media-assets/upload${query}`, {
      method: 'POST',
      body: fd,
    })
  },
}

export const imageUrl = (filename: string) => `/images/${filename}`

/** 下载图片原图，name 为期望文件名（同源资源，download 属性生效） */
export function downloadImage(filename: string, name: string) {
  const ext = filename.slice(filename.lastIndexOf('.')) || '.png'
  const a = document.createElement('a')
  a.href = imageUrl(filename)
  a.download = name.endsWith(ext) ? name : `${name}${ext}`
  document.body.appendChild(a)
  a.click()
  a.remove()
}
