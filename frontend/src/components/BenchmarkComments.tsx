import { useEffect, useState } from 'react'
import { App as AntApp, Button, Dropdown, Input, Spin } from 'antd'
import { EllipsisOutlined } from '@ant-design/icons'
import type { BenchmarkComment, VideoBenchmarkItem } from '../types'
import { videoBenchmarkApi } from '../api'

const { TextArea } = Input

const COMMENT_AUTHOR_KEY = 'benchmark_comment_author'

function formatCommentTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${d.getMonth() + 1}月${d.getDate()}日 ${hh}:${mi}`
}

export default function CommentsSection({
  item,
  onItemChange,
  bare = false,
}: {
  item: VideoBenchmarkItem
  onItemChange: (updated: VideoBenchmarkItem) => void
  /** bare: 去掉顶部分隔线和上边距，用于弹窗内嵌 */
  bare?: boolean
}) {
  const { message, modal } = AntApp.useApp()
  const [comments, setComments] = useState<BenchmarkComment[]>([])
  const [loading, setLoading] = useState(false)
  const [author, setAuthor] = useState(
    () => localStorage.getItem(COMMENT_AUTHOR_KEY) || '',
  )
  const [editingName, setEditingName] = useState(
    () => !localStorage.getItem(COMMENT_AUTHOR_KEY),
  )
  const [body, setBody] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    let alive = true
    setLoading(true)
    videoBenchmarkApi
      .listComments(item.id)
      .then((cs) => alive && setComments(cs))
      .catch((e) => message.error((e as Error).message))
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item.id])

  const submit = async () => {
    if (!body.trim()) {
      message.warning('请输入评论内容')
      return
    }
    setSubmitting(true)
    try {
      const created = await videoBenchmarkApi.addComment(item.id, author.trim(), body.trim())
      localStorage.setItem(COMMENT_AUTHOR_KEY, author.trim())
      setEditingName(false)
      setComments((prev) => [...prev, created])
      setBody('')
      onItemChange(await videoBenchmarkApi.get(item.id))
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  const remove = async (cid: number) => {
    try {
      await videoBenchmarkApi.deleteComment(cid)
      setComments((prev) => prev.filter((c) => c.id !== cid))
      onItemChange(await videoBenchmarkApi.get(item.id))
    } catch (e) {
      message.error((e as Error).message)
    }
  }

  return (
    <div
      style={
        bare
          ? {}
          : { marginTop: 28, paddingTop: 16, borderTop: '1px solid #e8e8e8' }
      }
    >
      {loading && (
        <div style={{ textAlign: 'center', padding: '16px 0' }}>
          <Spin size="small" />
        </div>
      )}

      {!loading && comments.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 18, marginBottom: 20 }}>
            {comments.map((c) => (
              <div key={c.id} className="comment-item">
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    background: '#f3f4f6',
                    borderRadius: 4,
                    padding: '5px 10px',
                  }}
                >
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#1f2328' }}>
                    {c.author || '匿名'}
                  </span>
                  <span style={{ fontSize: 12, color: '#9aa0a6' }}>
                    {formatCommentTime(c.created_at)}
                  </span>
                  <Dropdown
                    trigger={['click']}
                    menu={{
                      items: [
                        {
                          key: 'delete',
                          label: '删除',
                          danger: true,
                          onClick: () =>
                            modal.confirm({
                              title: '删除这条评论？',
                              okText: '删除',
                              okButtonProps: { danger: true },
                              cancelText: '取消',
                              onOk: () => remove(c.id),
                            }),
                        },
                      ],
                    }}
                  >
                    <Button
                      type="text"
                      size="small"
                      className="comment-more"
                      icon={<EllipsisOutlined />}
                      style={{ marginLeft: 'auto', color: '#9aa0a6' }}
                    />
                  </Dropdown>
                </div>
                <div
                  style={{
                    whiteSpace: 'pre-wrap',
                    fontSize: 14,
                    lineHeight: 1.6,
                    color: '#3a3f45',
                    padding: '8px 10px 0',
                  }}
                >
                  {c.body}
                </div>
              </div>
            ))}
          </div>
      )}

      <div>
        {editingName ? (
          <Input
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
            placeholder="首次评论请填写你的名字，后续会记住"
            style={{ marginBottom: 8 }}
          />
        ) : (
          <div
            style={{
              marginBottom: 8,
              paddingLeft: 11,
              fontSize: 13,
              fontWeight: 600,
              color: '#1f2328',
            }}
          >
            {author}
          </div>
        )}
        <TextArea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          autoSize={{ minRows: 3, maxRows: 10 }}
          placeholder="输入评论"
        />
        <div style={{ marginTop: 10, textAlign: 'right' }}>
          <Button onClick={() => setBody('')} style={{ marginRight: 8 }}>
            取消
          </Button>
          <Button type="primary" loading={submitting} onClick={submit}>
            发送
          </Button>
        </div>
      </div>
    </div>
  )
}
