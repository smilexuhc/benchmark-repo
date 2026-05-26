export interface QuestionTypeOption {
  value: string
  label: string
  children?: QuestionTypeOption[]
}

export const QUESTION_TYPE_OPTIONS: QuestionTypeOption[] = [
  {
    value: '单镜头',
    label: '单镜头',
    children: [
      {
        value: '1.创作意图与提示词理解/遵循',
        label: '1.创作意图与提示词理解/遵循',
        children: [
          { value: '极简提示词理解', label: '1.极简提示词理解' },
          { value: '主体、动作、场景核心基础测试', label: '2.主体、动作、场景核心基础测试' },
          { value: '复杂提示词与多条件约束遵循', label: '3.复杂提示词与多条件约束遵循' },
          { value: '抽象语义、情绪描述与隐喻理解', label: '4.抽象语义、情绪描述与隐喻理解' },
          { value: '专业剧本术语与创作指令理解', label: '5.专业剧本术语与创作指令理解' },
          { value: '动作顺序与因果关系遵循', label: '6.动作顺序与因果关系遵循' },
          { value: '否定约束遵循', label: '7.否定约束遵循' },
          { value: '参考资产继承范围控制', label: '8.参考资产继承范围控制' },
        ],
      },
      {
        value: '2.人物与主体呈现',
        label: '2.人物与主体呈现',
        children: [
          { value: '人物身份与人脸稳定性', label: '1.人物身份与人脸稳定性' },
          { value: '服饰、发型、配饰一致性', label: '2.服饰、发型、配饰一致性' },
          { value: '人物体态、年龄、肤色稳定性', label: '3.人物体态、年龄、肤色稳定性' },
          { value: '动物与非人主体真实感', label: '4.动物与非人主体真实感' },
          { value: '多主体复杂稳定性', label: '5.多主体复杂稳定性' },
        ],
      },
      {
        value: '3.场面调度与空间关系',
        label: '3.场面调度与空间关系',
        children: [
          { value: '人物站位合理性', label: '1.人物站位合理性' },
          { value: '主次关系与画面重心', label: '2.主次关系与画面重心' },
          { value: '人物距离与互动空间', label: '3.人物距离与互动空间' },
          { value: '大小比例与透视关系', label: '4.大小比例与透视关系' },
          { value: '出入画或运动动线', label: '5.出入画或运动动线' },
          { value: '复杂多人站位', label: '6.复杂多人站位' },
        ],
      },
      {
        value: '4.动作、表演与物理反馈',
        label: '4.动作、表演与物理反馈',
        children: [
          { value: '简单动作执行', label: '1.简单动作执行' },
          { value: '复杂动作执行', label: '2.复杂动作执行' },
          { value: '精细动作与手部表现', label: '3.精细动作与手部表现' },
          { value: '表情、眼神与微表情', label: '4.表情、眼神与微表情' },
          { value: '动作连续性与姿态稳定', label: '5.动作连续性与姿态稳定' },
          { value: '受力、碰撞与攻击反馈', label: '6.受力、碰撞与攻击反馈' },
          { value: '行为逻辑合理性', label: '7.行为逻辑合理性' },
        ],
      },
      {
        value: '5.场景、道具与画面融合',
        label: '5.场景、道具与画面融合',
        children: [
          { value: '场景布局合理性', label: '1.场景布局合理性' },
          { value: '人物与场景融合度', label: '2.人物与场景融合度' },
          { value: '人物与场景交互', label: '3.人物与场景交互' },
          { value: '道具比例与材质可信度', label: '4.道具比例与材质可信度' },
          { value: '道具使用与物理接触', label: '5.道具使用与物理接触' },
          { value: '自然现象与物质模拟', label: '6.自然现象与物质模拟' },
          { value: '画面文字渲染', label: '7.画面文字渲染' },
          { value: '光影、色调与质感', label: '8.光影、色调与质感' },
        ],
      },
      {
        value: '6.镜头语言与视觉风格',
        label: '6.镜头语言与视觉风格',
        children: [
          { value: '景别、构图与主体位置', label: '1.景别、构图与主体位置' },
          { value: '基础运镜执行', label: '2.基础运镜执行' },
          { value: '复杂运镜执行', label: '3.复杂运镜执行' },
          { value: '焦段、景深、焦点、曝光控制', label: '4.焦段、景深、焦点、曝光控制' },
          { value: '镜头节奏与视觉重点', label: '5.镜头节奏与视觉重点' },
          { value: '变速摄影控制', label: '6.变速摄影控制' },
          { value: '自然镜头切换合理性', label: '7.自然镜头切换合理性' },
          { value: '视觉风格控制', label: '8.视觉风格控制' },
        ],
      },
      {
        value: '7.台词、声音与字幕控制',
        label: '7.台词、声音与字幕控制',
        children: [
          { value: '台词文本遵循', label: '1.台词文本遵循' },
          { value: '台词、旁白与内心独白归属', label: '2.台词、旁白与内心独白归属' },
          { value: '口型与发声同步', label: '3.口型与发声同步' },
          { value: '语速、语气与情绪表达', label: '4.语速、语气与情绪表达' },
          { value: '人物音色与参考音频一致性', label: '5.人物音色与参考音频一致性' },
          { value: '音乐风格与画面匹配', label: '6.音乐风格与画面匹配' },
          { value: '音效对象、时机与质感', label: '7.音效对象、时机与质感' },
          { value: '字幕内容、样式与位置控制', label: '8.字幕内容、样式与位置控制' },
        ],
      },
    ],
  },
  {
    value: '连续镜头 2*15s',
    label: '连续镜头 2*15s',
    children: [
      {
        value: '1.跨镜头人物与主体连续性',
        label: '1.跨镜头人物与主体连续性',
        children: [
          { value: '人脸及人物特征连续性', label: '1.人脸及人物特征连续性' },
          { value: '服饰、发型、配饰连续性', label: '2.服饰、发型、配饰连续性' },
          { value: '人物状态连续性', label: '3.人物状态连续性' },
          { value: '多人物身份区分与防串脸', label: '4.多人物身份区分与防串脸' },
          { value: '动物与非人主体连续性', label: '5.动物与非人主体连续性' },
          { value: '参考主体跨镜头保持', label: '6.参考主体跨镜头保持' },
        ],
      },
      {
        value: '2.站位、空间与调度连续性',
        label: '2.站位、空间与调度连续性',
        children: [
          { value: '相邻镜头站位衔接', label: '1.相邻镜头站位衔接' },
          { value: '人物朝向与视线衔接', label: '2.人物朝向与视线衔接' },
          { value: '人物距离与空间关系衔接', label: '3.人物距离与空间关系衔接' },
          { value: '出入画动线衔接', label: '4.出入画动线衔接' },
          { value: '多人站位关系衔接', label: '5.多人站位关系衔接' },
          { value: '镜头切换后的透视与比例一致', label: '6.镜头切换后的透视与比例一致' },
        ],
      },
      {
        value: '3.动作与剪辑连续性',
        label: '3.动作与剪辑连续性',
        children: [
          { value: '动作姿态接续', label: '1.动作姿态接续' },
          { value: '动作方向接续', label: '2.动作方向接续' },
          { value: '动作节奏接续', label: '3.动作节奏接续' },
          { value: '受击、碰撞与反馈接续', label: '4.受击、碰撞与反馈接续' },
          { value: '中景到近景的连续性', label: '5.中景到近景的连续性' },
          { value: '剪辑点可用性', label: '6.剪辑点可用性' },
        ],
      },
      {
        value: '4.场景、时间与世界状态连续性',
        label: '4.场景、时间与世界状态连续性',
        children: [
          { value: '场景布置及状态连续性', label: '1.场景布置及状态连续性' },
          { value: '时间、天气与光影连续性', label: '2.时间、天气与光影连续性' },
          { value: '道具位置与外观连续性', label: '3.道具位置与外观连续性' },
          { value: '道具损坏、展开、变形状态连续性', label: '4.道具损坏、展开、变形状态连续性' },
          { value: '人物与道具交互结果连续性', label: '5.人物与道具交互结果连续性' },
          { value: '场景回访一致性', label: '6.场景回访一致性' },
        ],
      },
      {
        value: '5.声音、台词与字幕连续性',
        label: '5.声音、台词与字幕连续性',
        children: [
          { value: '人物音色跨镜头连续性', label: '1.人物音色跨镜头连续性' },
          { value: '语气、节奏与情绪连续性', label: '2.语气、节奏与情绪连续性' },
          { value: '对话关系与说话对象连续性', label: '3.对话关系与说话对象连续性' },
          { value: '口型与台词跨镜头衔接', label: '4.口型与台词跨镜头衔接' },
          { value: '背景音乐与音效连续性', label: '5.背景音乐与音效连续性' },
        ],
      },
    ],
  },
  {
    value: '长视频 60s',
    label: '长视频 60s',
    children: [
      {
        value: '1.剧本覆盖基础测试',
        label: '1.剧本覆盖基础测试',
        children: [
          { value: '关键场景覆盖', label: '1.关键场景覆盖' },
          { value: '关键角色覆盖', label: '2.关键角色覆盖' },
          { value: '关键动作与事件覆盖', label: '3.关键动作与事件覆盖' },
          { value: '多场景切换合理性', label: '4.多场景切换合理性' },
          { value: '整段主题与情绪基调保持', label: '5.整段主题与情绪基调保持' },
        ],
      },
      {
        value: '2.长程主体一致性',
        label: '2.长程主体一致性',
        children: [
          { value: '角色长程一致性（形象、状态）', label: '1.角色长程一致性（形象、状态）' },
          { value: '角色情绪变化合理性', label: '2.角色情绪变化合理性' },
          { value: '多角色关系保持', label: '3.多角色关系保持' },
          { value: '人物声音长程一致性', label: '4.人物声音长程一致性' },
        ],
      },
      {
        value: '3.长程场面调度与空间关系',
        label: '3.长程场面调度与空间关系',
        children: [
          { value: '多镜头站位连续性', label: '1.多镜头站位连续性' },
          { value: '多人物调度连续性', label: '2.多人物调度连续性' },
          { value: '空间关系长程稳定性', label: '3.空间关系长程稳定性' },
          { value: '同一场景回访一致性', label: '4.同一场景回访一致性' },
          { value: '人物移动路径连续性', label: '5.人物移动路径连续性' },
          { value: '场景切换中的方位感保持', label: '6.场景切换中的方位感保持' },
        ],
      },
      {
        value: '4.长程世界状态追踪',
        label: '4.长程世界状态追踪',
        children: [
          { value: '场景状态延续', label: '1.场景状态延续' },
          { value: '道具状态延续', label: '2.道具状态延续' },
          { value: '人物受伤、脏污、疲惫状态延续', label: '3.人物受伤、脏污、疲惫状态延续' },
          { value: '天气、时间与光影变化延续', label: '4.天气、时间与光影变化延续' },
          { value: '战斗、破坏与特效结果延续', label: '5.战斗、破坏与特效结果延续' },
          { value: '世界状态变化符合剧情因果', label: '6.世界状态变化符合剧情因果' },
        ],
      },
      {
        value: '5.长程动作、特效与镜头节奏',
        label: '5.长程动作、特效与镜头节奏',
        children: [
          { value: '复杂动作段落连续性', label: '1.复杂动作段落连续性' },
          { value: '打斗与攻击反馈连续性', label: '2.打斗与攻击反馈连续性' },
          { value: '特效与人物/场景融合', label: '3.特效与人物/场景融合' },
          { value: '运镜与空间关系保持', label: '4.运镜与空间关系保持' },
          { value: '镜头节奏服务叙事', label: '5.镜头节奏服务叙事' },
          { value: '动作段落成片可剪辑性', label: '6.动作段落成片可剪辑性' },
        ],
      },
      {
        value: '6.整段交付可用性',
        label: '6.整段交付可用性',
        children: [
          { value: '一分钟样片完整度', label: '1.一分钟样片完整度' },
          { value: '穿帮严重程度', label: '2.穿帮严重程度' },
        ],
      },
    ],
  },
]

export interface StatsGroup {
  shot_type: string
  question_type: string
  count: number
}

export const UNCLASSIFIED_L2_VALUE = '__unclassified__'

// 把 (shot_type, question_type) 题数统计拼到 Cascader 选项 label 上 -> "原 label (N)"
// L3 精确匹配；L2 = 子 L3 之和 + 「待归类」收尾；L1 = 该 shot_type 全量。
// 不在树里的 legacy question_type 自动归入「待归类」L2，避免被统计遗漏。
export function buildCascaderOptionsWithCounts(
  groups: StatsGroup[],
): QuestionTypeOption[] {
  const byShotQ = new Map<string, number>()
  for (const g of groups) {
    byShotQ.set(`${g.shot_type}|${g.question_type}`, g.count)
  }
  const withCount = (label: string, count: number) => `${label} (${count})`
  // 树里已知的 (shot_type|question_type) 集合，用于挑出 legacy
  const knownPairs = new Set<string>()
  for (const l1 of QUESTION_TYPE_OPTIONS) {
    for (const l2 of l1.children ?? []) {
      for (const l3 of l2.children ?? []) {
        knownPairs.add(`${l1.value}|${l3.value}`)
      }
    }
  }
  return QUESTION_TYPE_OPTIONS.map((l1) => {
    let l1Count = 0
    const l2List: QuestionTypeOption[] = (l1.children ?? []).map((l2) => {
      let l2Count = 0
      const l3s = (l2.children ?? []).map((l3) => {
        const count = byShotQ.get(`${l1.value}|${l3.value}`) || 0
        l2Count += count
        return { ...l3, label: withCount(l3.label, count) }
      })
      l1Count += l2Count
      return { ...l2, label: withCount(l2.label, l2Count), children: l3s }
    })
    // 收集该 shot_type 下所有 legacy 的 question_type
    const legacy: QuestionTypeOption[] = []
    let legacyCount = 0
    for (const [key, count] of byShotQ) {
      const [shot, q] = key.split('|')
      if (shot !== l1.value) continue
      if (!q) continue
      if (knownPairs.has(key)) continue
      legacy.push({ value: q, label: withCount(q, count) })
      legacyCount += count
    }
    if (legacy.length > 0) {
      legacy.sort((a, b) => a.value.localeCompare(b.value))
      l2List.push({
        value: UNCLASSIFIED_L2_VALUE,
        label: withCount('待归类', legacyCount),
        children: legacy,
      })
      l1Count += legacyCount
    }
    return {
      ...l1,
      label: withCount(l1.label, l1Count),
      children: l2List,
    }
  })
}

// 根据 shot_type + question_type 反向查找 Cascader 当前值（[L1.value, L2.value, L3.value]）
export function findCascaderValue(
  shotType: string,
  questionType: string,
): string[] | undefined {
  const l1 = QUESTION_TYPE_OPTIONS.find((o) => o.value === shotType)
  if (!l1) return undefined
  for (const l2 of l1.children ?? []) {
    const l3 = l2.children?.find((o) => o.value === questionType)
    if (l3) return [l1.value, l2.value, l3.value]
  }
  return undefined
}

// 反查 Cascader 路径上的 label（带序号），用于卡片标题展示
export function findCascaderLabels(
  shotType: string,
  questionType: string,
): string[] | undefined {
  const l1 = QUESTION_TYPE_OPTIONS.find((o) => o.value === shotType)
  if (!l1) return undefined
  for (const l2 of l1.children ?? []) {
    const l3 = l2.children?.find((o) => o.value === questionType)
    if (l3) return [l1.label, l2.label, l3.label]
  }
  return undefined
}
