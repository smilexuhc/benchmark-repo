import { useEffect, useRef, useState } from 'react'
import type { CSSProperties, ComponentProps } from 'react'
import { Image } from 'antd'

type AntdImageProps = ComponentProps<typeof Image>

interface Props extends AntdImageProps {
  rootMargin?: string
  placeholderStyle?: CSSProperties
}

export default function LazyImage({
  rootMargin = '200px',
  placeholderStyle,
  style,
  ...rest
}: Props) {
  const [inView, setInView] = useState(false)
  const holderRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (inView) return
    const el = holderRef.current
    if (!el) return
    if (typeof IntersectionObserver === 'undefined') {
      setInView(true)
      return
    }
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setInView(true)
          obs.disconnect()
        }
      },
      { rootMargin },
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [inView, rootMargin])

  if (inView) {
    return <Image style={style} {...rest} />
  }

  return (
    <div
      ref={holderRef}
      style={{
        background: '#f4f5f7',
        borderRadius: 4,
        ...style,
        ...placeholderStyle,
      }}
    />
  )
}
