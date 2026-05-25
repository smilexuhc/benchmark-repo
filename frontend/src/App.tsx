import { useState } from 'react'
import { Segmented, Tag } from 'antd'
import type { Character, Scene } from './types'
import {
  CHARACTER_FILTER_FIELDS, SCENE_FILTER_FIELDS, FIELD_LABELS,
} from './types'
import { characterApi, sceneApi } from './api'
import AssetLibrary from './components/AssetLibrary'
import BenchmarkItemsPage from './components/BenchmarkItemsPage'
import CharacterDrawer from './components/CharacterDrawer'
import SceneDrawer from './components/SceneDrawer'
import SceneViewColumn from './components/SceneViewColumn'

function InfoRow({ label, value }: { label: string; value: string }) {
  if (!value) return null
  return (
    <div style={{ display: 'flex', gap: 6, fontSize: 12, lineHeight: '20px' }}>
      <span style={{ color: '#9aa0a6', flexShrink: 0 }}>{label}</span>
      <span style={{ color: '#3a3f45' }}>{value}</span>
    </div>
  )
}

function Title({ text }: { text: string }) {
  return (
    <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>{text}</div>
  )
}

function Attrs({ text }: { text: string }) {
  return (
    <div style={{ fontSize: 12, color: '#9aa0a6', marginBottom: 10 }}>
      {text || '—'}
    </div>
  )
}

function GenreTag({ genre }: { genre: string }) {
  if (!genre) return null
  return (
    <div style={{ marginTop: 6 }}>
      <Tag color="blue" style={{ marginInlineEnd: 0 }}>
        {genre}
      </Tag>
    </div>
  )
}

function characterInfo(c: Character) {
  return (
    <>
      <Title text={c.persona || '(未命名)'} />
      <Attrs text={[c.era, c.type, c.gender, c.age].filter(Boolean).join(' · ')} />
      <InfoRow label="身材" value={c.body} />
      <InfoRow label="特征" value={c.features} />
      <GenreTag genre={c.genre} />
    </>
  )
}

function sceneInfo(s: Scene) {
  return (
    <>
      <Title text={s.name || '(未命名)'} />
      <Attrs text={[s.era, s.scene_type, s.mood].filter(Boolean).join(' · ')} />
      <InfoRow label="关键元素" value={s.elements} />
      <GenreTag genre={s.genre} />
    </>
  )
}

export default function App() {
  const [tab, setTab] = useState<'character' | 'scene' | 'benchmark'>('character')

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <header
        style={{
          height: 56,
          flexShrink: 0,
          background: '#fff',
          borderBottom: '1px solid #e8e8e8',
          display: 'flex',
          alignItems: 'center',
          padding: '0 20px',
          gap: 20,
        }}
      >
        <span style={{ fontSize: 16, fontWeight: 700 }}>资产库</span>
        <Segmented
          value={tab}
          onChange={(v) => setTab(v as 'character' | 'scene' | 'benchmark')}
          options={[
            { label: '角色资产库', value: 'character' },
            { label: '场景资产库', value: 'scene' },
            { label: '题目', value: 'benchmark' },
          ]}
        />
      </header>

      {tab === 'character' ? (
        <AssetLibrary<Character>
          api={characterApi}
          filterFields={CHARACTER_FILTER_FIELDS}
          filterLabels={FIELD_LABELS}
          renderInfo={characterInfo}
          nameOf={(c) => c.persona || '角色'}
          searchPlaceholder="搜索人设 / 特征 / 提示词"
          newLabel="新建角色"
          Drawer={CharacterDrawer}
        />
      ) : tab === 'scene' ? (
        <AssetLibrary<Scene>
          api={sceneApi}
          filterFields={SCENE_FILTER_FIELDS}
          filterLabels={FIELD_LABELS}
          renderInfo={sceneInfo}
          nameOf={(s) => s.name || '场景'}
          searchPlaceholder="搜索场景名 / 关键元素 / 提示词"
          newLabel="新建场景"
          Drawer={SceneDrawer}
          renderExtra={(s, refresh) => (
            <SceneViewColumn scene={s} onRefresh={refresh} />
          )}
        />
      ) : (
        <BenchmarkItemsPage />
      )}
    </div>
  )
}
