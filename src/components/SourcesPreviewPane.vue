<template>
  <!-- UTF-8：参考来源预览侧栏（支持多种文件类型） -->
  <a-drawer :open="visible" :width="560" placement="right" :closable="true" @close="$emit('close')">
    <template #title>
      <div class="drawer-title">
        <span>参考来源</span>
        <a-tag v-if="sources && sources.length" color="blue">{{ sources.length }}</a-tag>
      </div>
    </template>

    <div class="pane">
      <div class="list">
        <a-list :data-source="sources || []" size="small" :locale="{ emptyText: '暂无来源' }">
          <template #renderItem="{ item, index }">
            <a-list-item class="src-item" :class="{ active: activeIndex===index }" @click="openSource(item, index)">
              <file-text-outlined />
              <span class="name" :title="getName(item)">{{ getName(item) }}</span>
            </a-list-item>
          </template>
        </a-list>
      </div>

      <div class="preview">
        <div v-if="!preview.url" class="placeholder">
          <file-text-outlined class="ph-icon" />
          <p>点击左侧来源进行预览</p>
        </div>

        <!-- 图片 -->
        <div v-else-if="preview.viewer === 'image'" class="viewer image">
          <img :src="preview.objectUrl || preview.url" alt="预览图片" />
        </div>

        <!-- Markdown -->
        <div v-else-if="preview.viewer === 'markdown'" class="viewer md" v-html="preview.html"></div>

        <!-- JSON / 文本 -->
        <pre v-else-if="preview.viewer === 'json' || preview.viewer === 'text'" class="viewer code">{{ preview.text }}</pre>

        <!-- Excel：多表预览 -->
        <div v-else-if="preview.viewer === 'excel'" class="viewer excel">
          <a-tabs type="card" size="small">
            <a-tab-pane v-for="(sheet, i) in preview.sheets" :key="i" :tab="sheet.name || ('Sheet' + (i + 1))">
              <div class="sheet-html" v-html="sheet.html"></div>
            </a-tab-pane>
          </a-tabs>
        </div>

        <!-- Word：docx-preview 渲染容器 -->
        <div v-else-if="preview.viewer === 'word'" ref="docxEl" class="viewer docx"></div>

        <!-- HTML 文件 -->
        <div v-else-if="preview.viewer === 'html'" class="viewer html" v-html="preview.html"></div>

        <!-- PDF / 其它兜底（iframe） -->
        <iframe v-else :src="preview.url" class="viewer iframe" referrerpolicy="no-referrer"></iframe>
      </div>
    </div>
  </a-drawer>
</template>

<script setup>
// 说明：抽取自 RagChat 的预览逻辑，做成通用参考来源预览面板
import { ref, reactive, nextTick } from 'vue'
import { FileTextOutlined } from '@ant-design/icons-vue'
import KnowledgeBaseService from '@/services/knowledgeBase'
import { renderAsync as renderDocx } from 'docx-preview'
import * as XLSX from 'xlsx'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({ html: true, breaks: true, linkify: true })

const props = defineProps({
  visible: { type: Boolean, default: false },
  // 来源数组，约定字段：file_id/filename/title/source_file/url
  sources: { type: Array, default: () => [] }
})

const emit = defineEmits(['close'])

// 状态
const activeIndex = ref(-1)
const docxEl = ref(null)
const preview = reactive({
  url: '', filename: '', mime: '', ext: '', viewer: '', objectUrl: '', text: '', html: '', sheets: []
})

// 工具
const getName = (s) => s?.filename || s?.title || s?.source_file || s?.url || '来源'
function getExt(name = '') { const m = name.toLowerCase().match(/\.([a-z0-9]+)(?:\?.*)?$/); return m ? m[1] : '' }
async function sniffMime(url) { try { const res = await fetch(url, { method: 'HEAD' }); return res.headers.get('content-type') || '' } catch { return '' } }
function chooseViewer({ ext, mime }) {
  const e = ext; const m = (mime || '').toLowerCase()
  if (m.includes('pdf') || e === 'pdf') return 'pdf'
  if (m.startsWith('image/') || ['png','jpg','jpeg','gif','webp','bmp','svg'].includes(e)) return 'image'
  if (e === 'md' || m.includes('text/markdown')) return 'markdown'
  if (e === 'json' || m.includes('application/json')) return 'json'
  if (['txt','log','csv','tsv','py','js','ts','yml','yaml','ini','cfg'].includes(e) || m.startsWith('text/')) return 'text'
  if (['xlsx','xls'].includes(e) || m.includes('spreadsheet')) return 'excel'
  if (e === 'docx' || m.includes('wordprocessingml')) return 'word'
  if (e === 'html' || e === 'htm' || m.includes('text/html')) return 'html'
  return 'iframe'
}

// 打开来源
async function openSource(s, index = 0) {
  activeIndex.value = index
  // 没有 file_id 的情况下，直接用 url
  let url = s?.url
  let filename = s?.filename || s?.title || s?.source_file || ''
  try{
    if (s?.file_id) {
      const out = await KnowledgeBaseService.getFilePreviewUrl(s.file_id)
      url = out.url
      filename = out.filename || filename
    }
  } catch { /* 忽略 */ }

  await preparePreview({ url, filename })
}

// 准备预览
async function preparePreview({ url, filename }) {
  clearPreview()
  preview.url = url
  preview.filename = filename
  preview.ext = getExt(filename || url)
  preview.mime = await sniffMime(url)
  preview.viewer = chooseViewer({ ext: preview.ext, mime: preview.mime })

  // PDF 适配参数
  if (preview.viewer === 'pdf') {
    const hasHash = preview.url.includes('#')
    const pdfParams = 'toolbar=0&navpanes=0&view=FitH'
    preview.url = hasHash ? `${preview.url}&${pdfParams}` : `${preview.url}#${pdfParams}`
  }

  try{
    switch (preview.viewer) {
      case 'image': {
        break
      }
      case 'markdown': {
        const text = await (await fetch(url)).text()
        preview.html = md.render(text || '')
        break
      }
      case 'json': {
        const text = await (await fetch(url)).text()
        try { preview.text = JSON.stringify(JSON.parse(text), null, 2) } catch { preview.text = text }
        break
      }
      case 'text': {
        preview.text = await (await fetch(url)).text()
        break
      }
      case 'excel': {
        const buf = await (await fetch(url)).arrayBuffer()
        const wb = XLSX.read(buf, { type: 'array' })
        preview.sheets = wb.SheetNames.map(name => {
          const ws = wb.Sheets[name]
          const html = XLSX.utils.sheet_to_html(ws, { id: name, editable: false, header: '', footer: '' })
          return { name, html }
        })
        break
      }
      case 'word': {
        const blob = await (await fetch(url)).blob()
        await nextTick()
        if (docxEl.value) await renderDocx(blob, docxEl.value, undefined, { className: 'docx' })
        break
      }
      case 'html': {
        preview.html = await (await fetch(url)).text()
        break
      }
      default: break
    }
  }catch{
    preview.viewer = 'iframe'
  }
}

function clearPreview(){
  if (preview.objectUrl) { URL.revokeObjectURL(preview.objectUrl); preview.objectUrl = '' }
  preview.url=''; preview.filename=''; preview.mime=''; preview.ext=''; preview.viewer=''; preview.text=''; preview.html=''; preview.sheets=[]
}
</script>

<style scoped>
.drawer-title{ display:flex; align-items:center; gap:8px; font-weight:600; }
.pane{ display:grid; grid-template-columns: 220px 1fr; gap:12px; height: calc(100vh - 120px); }
.list{ overflow:auto; border-right:1px solid #eef0f3; padding-right:8px; }
.src-item{ display:flex; align-items:center; gap:8px; cursor:pointer; padding:6px 4px; border-radius:8px; }
.src-item:hover{ background:#f7f9fc; }
.src-item.active{ background:#eef2ff; }
.name{ white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.preview{ overflow:auto; padding-left:8px; }
.placeholder{ display:grid; place-items:center; height:100%; color:#94a3b8; }
.ph-icon{ font-size:24px; }
.viewer.image img{ max-width:100%; border-radius:8px; box-shadow: 0 4px 18px rgba(0,0,0,.06); }
.viewer.code{ background:#0b1020; color:#e5e7eb; padding:12px; border-radius:10px; border:1px solid #1f2937; }
.sheet-html :deep(table){ width:100%; border-collapse: collapse; }
.sheet-html :deep(td), .sheet-html :deep(th){ border:1px solid #eaeaea; padding:8px 10px; }
.viewer.html{ background:#fff; border:1px solid #eaeaea; border-radius:8px; padding:10px; }
.viewer.iframe{ width:100%; height: calc(100vh - 160px); border:none; border-radius:8px; }
</style>

