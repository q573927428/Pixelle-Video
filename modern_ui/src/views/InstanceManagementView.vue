<template>
  <div class="tool-page">
    <div class="page-header">
      <span class="page-icon">🖥️</span>
      <div>
        <h3 class="page-title">实例管理</h3>
        <p class="page-desc">AutoDL 实例生命周期管理 / 镜像机 ComfyUI 控制 / 自动扩缩容</p>
      </div>
    </div>

    <!-- 自动扩缩容状态 -->
    <div class="card" style="margin-bottom:18px;">
      <div class="card-header">
        <h3 class="card-title">🤖 自动扩缩容</h3>
      </div>
      <div class="card-body">
        <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
          <div>
            状态：
            <el-tag :type="scalingRunning ? 'success' : 'info'" size="small">
              {{ scalingRunning ? '运行中' : '已停止' }}
            </el-tag>
          </div>
          <div v-if="scalingRunning">
            <span class="small muted">空闲关机：{{ scalingConfig.idle_shutdown_minutes }} 分钟</span>
            <span style="margin:0 8px;">|</span>
            <span class="small muted">空闲释放：{{ scalingConfig.idle_release_days }} 天</span>
            <span style="margin:0 8px;">|</span>
            <span class="small muted">检查间隔：{{ scalingConfig.check_interval_seconds }} 秒</span>
          </div>
          <div style="margin-left:auto;display:flex;gap:8px;">
            <el-button
              :type="scalingRunning ? 'danger' : 'success'"
              size="small"
              :loading="scalingLoading"
              @click="toggleScaling"
            >
              {{ scalingRunning ? '停止监控' : '启动监控' }}
            </el-button>
            <el-button size="small" @click="refreshScalingStatus">🔄 刷新</el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 操作按钮栏 -->
    <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;">
      <el-button type="primary" @click="showListDialog = true">📋 拉取 AutoDL 实例列表</el-button>
      <el-button @click="showCreateDialog = true">➕ 新建实例</el-button>
      <el-button :loading="ensuringReady" @click="handleEnsureReady" type="success">⚡ 确保就绪实例</el-button>
    </div>

    <!-- 主控面板信息 -->
    <div v-if="panelBaseUrl" class="card" style="margin-bottom:18px;">
      <div class="card-body" style="display:flex;align-items:center;gap:8px;padding:8px 16px;">
        <span class="small muted">主控面板：</span>
        <code style="font-size:12px;">{{ panelBaseUrl }}</code>
        <span style="margin-left:auto;font-size:12px;color:var(--tx-2);">
          共 <strong>{{ instances.length }}</strong> 台，
          <strong style="color:#34d399;">{{ runningCount }}</strong> 台运行，
          <strong style="color:#fbbf24;">{{ shutdownCount }}</strong> 台关机
        </span>
      </div>
    </div>

    <!-- 实例列表 -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">📡 AutoDL 实例列表</h3>
        <el-button size="small" :loading="loadingList" @click="handleListInstances" style="margin-left:auto;">🔄 刷新列表</el-button>
      </div>
      <div class="card-body" style="padding:0;">
        <el-table :data="instances" style="width:100%;" stripe size="small" v-if="instances.length > 0">
          <el-table-column prop="name" label="名称" min-width="100" />
          <el-table-column prop="instance_uuid" label="UUID" min-width="110" show-overflow-tooltip />
          <el-table-column prop="gpu_name" label="GPU" width="120" />
          <el-table-column label="状态" width="180">
            <template #default="{ row }">
              <el-tag :type="row.status === 'running' ? 'success' : (row.status === 'starting' ? 'warning' : 'info')" size="small">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="ComfyUI" width="150">
            <template #default="{ row }">
              <el-tag :type="row.comfy_status === 'running' ? 'success' : (row.comfy_status === 'starting' ? 'warning' : 'info')" size="small">
                {{ row.comfy_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="面板地址" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">
              <a v-if="row.mirror_url" :href="row.mirror_url" target="_blank" style="font-size:11px;color:var(--primary);text-decoration:none;">
                {{ row.mirror_url }}
              </a>
              <span v-else class="muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="200" fixed="right">
            <template #default="{ row }">
              <div style="display:flex;gap:4px;flex-wrap:wrap;">
                <el-button
                  v-if="row.status === 'shutdown'"
                  size="small"
                  type="primary"
                  @click="handlePowerOn(row)"
                >开机</el-button>
                <el-button
                  v-if="row.status === 'running'"
                  size="small"
                  @click="handlePowerOff(row)"
                >关机</el-button>
                <el-button
                  v-if="!isMaster(row.instance_uuid)"
                  size="small"
                  type="danger"
                  @click="handleRelease(row)"
                >释放</el-button>
                <el-button
                  v-if="row.mirror_url"
                  size="small"
                  @click="showMirrorDialog(row)"
                >ComfyUI</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
        <div v-else style="padding:32px;text-align:center;color:var(--tx-2);">
          暂无实例数据。请先「拉取 AutoDL 实例列表」。
        </div>
      </div>
    </div>

    <!-- 拉取列表弹窗 -->
    <el-dialog v-model="showListDialog" title="拉取 AutoDL 实例列表" width="500px">
      <el-form label-position="top">
        <el-form-item label="AutoDL Token">
          <el-input v-model="listToken" type="password" show-password placeholder="autodl_xxx..." />
        </el-form-item>
        <div class="small muted" style="margin-top:-12px;padding-bottom:8px;">
          Token 在 https://www.autodl.com/console/center/settings/token 获取
        </div>
      </el-form>
      <template #footer>
        <el-button @click="showListDialog = false">取消</el-button>
        <el-button type="primary" :loading="loadingList" @click="handleListInstances">拉取</el-button>
      </template>
    </el-dialog>

    <!-- 新建实例弹窗 -->
    <el-dialog v-model="showCreateDialog" title="新建 AutoDL 实例" width="500px">
      <el-form label-position="top">
        <el-form-item label="AutoDL Token">
          <el-input v-model="createToken" type="password" show-password placeholder="autodl_xxx..." />
        </el-form-item>
        <el-form-item label="GPU 规格">
          <el-select v-model="createSpecUuid" style="width:100%;" filterable allow-create placeholder="选择或输入 GPU 规格 UUID">
            <el-option v-for="g in gpuSpecOptions" :key="g.value" :label="g.label" :value="g.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="实例名称">
          <el-input v-model="createName" placeholder="并发生成-镜像机" />
        </el-form-item>
        <el-form-item label="GPU 数量">
          <el-input-number v-model="createGpuAmount" :min="1" :max="8" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creatingInstance" @click="handleCreateInstance">创建</el-button>
      </template>
    </el-dialog>

    <!-- 镜像机 ComfyUI 控制弹窗 -->
    <el-dialog v-model="showMirrorDialogVisible" :title="`ComfyUI 控制 - ${mirrorTarget?.name}`" width="600px">
      <template v-if="mirrorTarget">
        <div style="margin-bottom:12px;">
          <div><strong>镜像机地址：</strong><code style="font-size:12px;">{{ mirrorTarget.mirror_url }}</code></div>
          <div style="margin-top:4px;">
            <strong>ComfyUI 状态：</strong>
            <el-tag :type="mirrorComfyRunning === 'running' ? 'success' : (mirrorComfyRunning === 'starting' ? 'warning' : 'info')" size="small">
              {{ mirrorComfyRunning }}
            </el-tag>
          </div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;">
          <el-button size="small" type="success" :loading="mirrorLoading" @click="handleMirrorStart">启动 ComfyUI</el-button>
          <el-button size="small" @click="handleMirrorStop" :loading="mirrorLoading">停止 ComfyUI</el-button>
          <el-button size="small" @click="handleMirrorInterrupt" :loading="mirrorLoading">中断任务</el-button>
          <el-button size="small" @click="handleMirrorFree" :loading="mirrorLoading">释放显存</el-button>
          <el-button size="small" @click="handleMirrorProbe" :loading="mirrorLoading">探测连通性</el-button>
          <el-button size="small" @click="handleMirrorRefreshStatus" :loading="mirrorLoading">刷新状态</el-button>
        </div>
        <el-divider />
        <div>
          <h4 style="margin:0 0 8px;font-size:13px;">版本切换</h4>
          <div style="display:flex;gap:8px;">
            <el-input v-model="mirrorVersion" placeholder="例如 0.25.1" style="flex:1;" size="small" />
            <el-button size="small" @click="handleMirrorVersions" :loading="mirrorLoading">查询版本</el-button>
            <el-button size="small" type="primary" @click="handleMirrorSwitchVersion" :loading="mirrorLoading">切换版本</el-button>
          </div>
          <div v-if="mirrorVersionList.length > 0" style="margin-top:8px;">
            <el-tag
              v-for="v in mirrorVersionList"
              :key="v.id"
              style="margin:2px;cursor:pointer;"
              :type="mirrorVersion === v.id ? 'primary' : 'info'"
              @click="mirrorVersion = v.id"
              size="small"
            >{{ v.label || v.id }}</el-tag>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listInstances as apiListInstances,
  getInstanceSnapshot,
  powerOnInstance,
  powerOffInstance,
  releaseInstance,
  createInstance,
  ensureReadyInstance,
  getAutoScalingStatus,
  startAutoScaling,
  stopAutoScaling,
  mirrorStartComfyui,
  mirrorStopComfyui,
  mirrorComfyStatus,
  mirrorInterrupt,
  mirrorFreeMemory,
  mirrorProbe,
  mirrorVersions,
  mirrorSwitchVersion,
  getConfig,
} from '../api'

// ========== Type ==========

interface InstanceItem {
  instance_uuid: string
  mirror_url: string
  status: string
  comfy_status: string
  name: string
  gpu_name: string
  auto_managed: boolean
  current_jobs: number
  total_jobs_completed: number
  last_active_time: string
  created_at: string
  power_on_time: string
  idle_seconds: number
  uptime_seconds: number
  age_days: number
}

// ========== State ==========

const instances = ref<InstanceItem[]>([])
const loadingList = ref(false)
const showListDialog = ref(false)
const listToken = ref(localStorage.getItem('pixelle_autodl_token') || '')

const showCreateDialog = ref(false)
const createToken = ref('')
const createSpecUuid = ref('')
const createName = ref('并发生成-镜像机')
const createGpuAmount = ref(1)
const creatingInstance = ref(false)

const scalingRunning = ref(false)
const scalingLoading = ref(false)
const scalingConfig = ref({
  idle_shutdown_minutes: 10,
  idle_release_days: 7,
  check_interval_seconds: 60,
})

const ensuringReady = ref(false)

// GPU 规格下拉选项
const gpuSpecOptions = [
  { value: '5090-p', label: 'RTX 5090 (5090-p)' },
  { value: 'pro6000-p', label: 'RTX PRO 6000 (pro6000-p)' },
  { value: '4090-p', label: 'RTX 4090 (4090-p)' },
  { value: '4080super-p', label: 'RTX 4080 Super (4080super-p)' },
  { value: 'a100-sxm', label: 'A100 SXM (a100-sxm)' },
]

const showMirrorDialogVisible = ref(false)
const mirrorTarget = ref<InstanceItem | null>(null)
const mirrorLoading = ref(false)
const mirrorComfyRunning = ref('unknown')
const mirrorVersion = ref('')
const mirrorVersionList = ref<any[]>([])

const panelBaseUrl = ref('')
const masterUuid = ref('')  // 主控机 UUID

// ========== Computed ==========

const runningCount = computed(() => instances.value.filter(i => i.status === 'running').length)
const shutdownCount = computed(() => instances.value.filter(i => i.status === 'shutdown').length)

/** 判断是否为 主控机（不显示释放按钮） */
function isMaster(uuid: string) {
  return masterUuid.value && uuid === masterUuid.value
}

// ========== Lifecycle ==========

onMounted(async () => {
  try {
    const cfg = await getConfig()
    const rc = cfg.comfyui?.remote_comfy
    if (rc?.base_url) {
      panelBaseUrl.value = rc.base_url
      // 从面板 URL 中提取主控机 UUID
      // URL 格式如: https://uu1068283-7826db062674.westd.seetacloud.com:8443
      // 对应 AutoDL 实例 UUID: pro-7826db062674
      const match = panelBaseUrl.value.match(/-([a-z0-9]{12})\./)
      if (match) {
        masterUuid.value = 'pro-' + match[1]
      }
    }
  } catch (_) {}
  await refreshScalingStatus()
  if (listToken.value) {
    await handleListInstances()
  }
})

// ========== Format Helpers ==========

function formatIdle(seconds: number) {
  if (!seconds || seconds < 60) return '刚活跃'
  const mins = Math.floor(seconds / 60)
  if (mins < 60) return `${mins} 分钟`
  return `${Math.floor(mins / 60)} 小时`
}

// ========== Auto-Scaling ==========

async function refreshScalingStatus() {
  try {
    const res = await getAutoScalingStatus()
    if (res.success) {
      scalingRunning.value = res.running
      scalingConfig.value.idle_shutdown_minutes = res.idle_shutdown_minutes
      scalingConfig.value.idle_release_days = res.idle_release_days
      scalingConfig.value.check_interval_seconds = res.check_interval_seconds
    }
  } catch (_) {}
}

async function toggleScaling() {
  scalingLoading.value = true
  try {
    if (scalingRunning.value) {
      await stopAutoScaling()
      ElMessage.success('自动扩缩容已停止')
    } else {
      if (!listToken.value) {
        ElMessage.warning('请先在「拉取实例列表」中输入 AutoDL Token')
        scalingLoading.value = false
        return
      }
      const startRes = await startAutoScaling(
        scalingConfig.value.idle_shutdown_minutes,
        scalingConfig.value.idle_release_days,
        listToken.value,
      )
      if (startRes.success) {
        ElMessage.success('自动扩缩容已启动')
      } else {
        ElMessage.error(startRes.message || '启动自动扩缩容失败')
      }
    }
    // 刷新状态（running 可能是 true/false 或 1/0，统一转为 boolean）
    const statusRes = await getAutoScalingStatus()
    if (statusRes.success) {
      scalingRunning.value = !!statusRes.running
    }
  } catch (e: any) {
    ElMessage.error(`操作失败：${e.message}`)
  } finally {
    scalingLoading.value = false
  }
}

// ========== List Instances ==========

async function handleListInstances() {
  if (!listToken.value) {
    ElMessage.warning('请输入 AutoDL Token')
    return
  }
  localStorage.setItem('pixelle_autodl_token', listToken.value)
  loadingList.value = true
  try {
    const res = await apiListInstances(listToken.value)
    console.log('[InstanceList] raw response:', JSON.stringify(res, null, 2))
    
    if (res.success) {
      const list: any[] = res.list || res.instances || []
      ElMessage.success(`成功拉取 ${list.length} 个实例`)

      // 自动探测第一个实例的所有字段
      if (list.length > 0) {
        const sample = list[0]
        console.log('[InstanceList] sample fields:', Object.keys(sample))
        console.log('[InstanceList] sample data:', JSON.stringify(sample, null, 2))
      }

      const gpuSpecNames: Record<string, string> = {
        '5090-p': 'RTX 5090',
        'pro6000-p': 'RTX PRO 6000',
        '4090-p': 'RTX 4090',
        '4080super-p': 'RTX 4080 Super',
        'a100-sxm': 'A100 SXM',
      }

      const newList: InstanceItem[] = []
      for (const item of list) {
        const old = instances.value.find(i => i.instance_uuid === (item.uuid || item.instance_uuid || item.id))
        const uuid = item.uuid || item.instance_uuid || item.id || ''
        
        // 已 running 的实例，异步查询 snapshot 获取域名的逻辑在下面
        const mirrorUrl = old?.mirror_url || ''
        
        const status = item.status || 'unknown'
        const specUuid = item.gpu_spec_uuid || ''
        const gpuName = gpuSpecNames[specUuid] || specUuid || ''
        
        const name = item.name || item.machine_alias || item.instance_name || uuid || '未知'

        newList.push({
          instance_uuid: uuid,
          mirror_url: mirrorUrl,
          status: status,
          comfy_status: old?.comfy_status || 'stopped',
          name: name,
          gpu_name: gpuName,
          auto_managed: old?.auto_managed || false,
          current_jobs: old?.current_jobs || 0,
          total_jobs_completed: old?.total_jobs_completed || 0,
          last_active_time: old?.last_active_time || new Date().toISOString(),
          created_at: old?.created_at || new Date().toISOString(),
          power_on_time: old?.power_on_time || '',
          idle_seconds: old?.idle_seconds || 0,
          uptime_seconds: old?.uptime_seconds || 0,
          age_days: old?.age_days || 0,
        })
      }
      instances.value = newList
      showListDialog.value = false

      // 非 running 状态强制设为 stopped
      for (const inst of instances.value) {
        if (inst.status !== 'running') {
          inst.comfy_status = 'stopped'
          inst.mirror_url = ''
        }
      }
      // 异步查询面板地址和 ComfyUI 状态（仅 running 实例）
      for (const inst of instances.value) {
        if (inst.status === 'running') {
          queryInstanceSnapshot(inst).catch(() => {})
        }
      }
    } else {
      ElMessage.error(res.message || '拉取失败')
    }
  } catch (e: any) {
    ElMessage.error(`拉取失败：${e.message}`)
  } finally {
    loadingList.value = false
  }
}

async function queryInstanceSnapshot(inst: InstanceItem) {
  if (!listToken.value) return
  try {
    // 通过 GET /api/instances/snapshot 获取 service_6008_domain
    const snapshot = await getInstanceSnapshot(listToken.value, inst.instance_uuid)
    console.log(`[Snapshot ${inst.name}]`, JSON.stringify(snapshot, null, 2))
    const snap = snapshot.snapshot || {}
    const domain = snap.service_6008_domain || snap.domain || ''
    if (domain) {
      inst.mirror_url = domain.startsWith('http') ? domain : 'https://' + domain
      // 获取到 panel 地址后查询 ComfyUI 状态
      queryComfyStatus(inst).catch(() => {})
    }
  } catch (_) {}
}

async function queryComfyStatus(inst: InstanceItem) {
  if (!inst.mirror_url) return
  try {
    const res = await mirrorComfyStatus(inst.mirror_url)
    if (res.running !== undefined) {
      inst.comfy_status = res.running ? 'running' : (res.starting ? 'starting' : 'stopped')
    }
  } catch (_) {
    inst.comfy_status = 'stopped'
  }
}

// ========== Power Actions ==========

async function handlePowerOn(row: InstanceItem) {
  if (!listToken.value) {
    ElMessage.warning('请先在「拉取实例列表」中输入 AutoDL Token')
    return
  }
  try {
    const res = await powerOnInstance(listToken.value, row.instance_uuid)
    if (res.success) {
      ElMessage.success(`开机指令已发送：${row.name}`)
      row.status = 'starting'
    } else {
      ElMessage.error(res.message || '开机失败')
    }
  } catch (e: any) {
    ElMessage.error(`开机失败：${e.message}`)
  }
}

async function handlePowerOff(row: InstanceItem) {
  if (!listToken.value) {
    ElMessage.warning('请先在「拉取实例列表」中输入 AutoDL Token')
    return
  }
  try {
    const res = await powerOffInstance(listToken.value, row.instance_uuid)
    if (res.success) {
      ElMessage.success(`关机指令已发送：${row.name}`)
      row.status = 'shutdown'
      row.mirror_url = ''
    } else {
      ElMessage.error(res.message || '关机失败')
    }
  } catch (e: any) {
    ElMessage.error(`关机失败：${e.message}`)
  }
}

async function handleRelease(row: InstanceItem) {
  if (!listToken.value) {
    ElMessage.warning('请先在「拉取实例列表」中输入 AutoDL Token')
    return
  }

  // 检测实例是否在运行中，运行中的实例必须先关机才能释放
  if (row.status === 'running' || row.status === 'starting') {
    ElMessage.warning(`实例「${row.name}」正在运行中，请先「关机」后再释放`)
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要释放实例「${row.name}」？\n释放后数据将永久丢失无法恢复！`,
      '确认释放',
      { confirmButtonText: '确认释放', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }

  try {
    const res = await releaseInstance(listToken.value, row.instance_uuid)
    if (res.success) {
      ElMessage.success(`已释放：${row.name}`)
      const idx = instances.value.indexOf(row)
      if (idx >= 0) instances.value.splice(idx, 1)
    } else {
      ElMessage.error(res.message || '释放失败')
    }
  } catch (e: any) {
    ElMessage.error(`释放失败：${e.message}`)
  }
}

async function handleCreateInstance() {
  if (!createToken.value) {
    ElMessage.warning('请输入 AutoDL Token')
    return
  }
  if (!createSpecUuid.value) {
    ElMessage.warning('请输入 GPU 规格 UUID')
    return
  }
  creatingInstance.value = true
  try {
    const res = await createInstance(createToken.value, createSpecUuid.value, createName.value, createGpuAmount.value)
    if (res.success) {
      ElMessage.success(`实例创建成功：${res.instance_uuid}`)
      showCreateDialog.value = false
      listToken.value = createToken.value
      await handleListInstances()
    } else {
      ElMessage.error(res.message || '创建失败')
    }
  } catch (e: any) {
    ElMessage.error(`创建失败：${e.message}`)
  } finally {
    creatingInstance.value = false
  }
}

async function handleEnsureReady() {
  ensuringReady.value = true
  try {
    const res = await ensureReadyInstance(listToken.value)
    if (res.success) {
      ElMessage.success(`就绪镜像机：${res.mirror_url}`)
      await refreshScalingStatus()
    } else {
      ElMessage.warning(res.message || '无法获取就绪镜像机')
    }
  } catch (e: any) {
    ElMessage.error(`操作失败：${e.message}`)
  } finally {
    ensuringReady.value = false
  }
}

// ========== Mirror ComfyUI Control ==========

function showMirrorDialog(row: InstanceItem) {
  mirrorTarget.value = row
  mirrorVersion.value = ''
  mirrorVersionList.value = []
  mirrorComfyRunning.value = row.comfy_status || 'unknown'
  showMirrorDialogVisible.value = true
  handleMirrorRefreshStatus()
}

async function handleMirrorRefreshStatus() {
  if (!mirrorTarget.value?.mirror_url) return
  mirrorLoading.value = true
  try {
    const res = await mirrorComfyStatus(mirrorTarget.value.mirror_url)
    if (res.running !== undefined) {
      mirrorComfyRunning.value = res.running ? 'running' : (res.starting ? 'starting' : 'stopped')
      mirrorTarget.value!.comfy_status = mirrorComfyRunning.value
    }
  } catch (e: any) {
    ElMessage.warning(`状态查询失败：${e.message}`)
  } finally {
    mirrorLoading.value = false
  }
}

async function handleMirrorStart() {
  if (!mirrorTarget.value?.mirror_url) return
  mirrorLoading.value = true
  try {
    const res = await mirrorStartComfyui(mirrorTarget.value.mirror_url)
    if (res.success !== false) {
      ElMessage.success('ComfyUI 启动指令已发送')
      mirrorComfyRunning.value = 'starting'
      mirrorTarget.value!.comfy_status = 'starting'
    } else {
      ElMessage.error(res.message || '启动失败')
    }
  } catch (e: any) {
    ElMessage.error(`启动失败：${e.message}`)
  } finally {
    mirrorLoading.value = false
  }
}

async function handleMirrorStop() {
  if (!mirrorTarget.value?.mirror_url) return
  mirrorLoading.value = true
  try {
    const res = await mirrorStopComfyui(mirrorTarget.value.mirror_url)
    if (res.success !== false) {
      ElMessage.success('ComfyUI 已停止')
      mirrorComfyRunning.value = 'stopped'
      mirrorTarget.value!.comfy_status = 'stopped'
    } else {
      ElMessage.error(res.message || '停止失败')
    }
  } catch (e: any) {
    ElMessage.error(`停止失败：${e.message}`)
  } finally {
    mirrorLoading.value = false
  }
}

async function handleMirrorInterrupt() {
  if (!mirrorTarget.value?.mirror_url) return
  mirrorLoading.value = true
  try {
    await mirrorInterrupt(mirrorTarget.value.mirror_url)
    ElMessage.success('中断指令已发送')
  } catch (e: any) {
    ElMessage.error(`中断失败：${e.message}`)
  } finally {
    mirrorLoading.value = false
  }
}

async function handleMirrorFree() {
  if (!mirrorTarget.value?.mirror_url) return
  mirrorLoading.value = true
  try {
    await mirrorFreeMemory(mirrorTarget.value.mirror_url)
    ElMessage.success('显存释放指令已发送')
  } catch (e: any) {
    ElMessage.error(`释放失败：${e.message}`)
  } finally {
    mirrorLoading.value = false
  }
}

async function handleMirrorProbe() {
  if (!mirrorTarget.value?.mirror_url) return
  mirrorLoading.value = true
  try {
    const res = await mirrorProbe(mirrorTarget.value.mirror_url)
    if (res.success !== false) {
      ElMessage.success('镜像机连通正常')
    } else {
      ElMessage.warning('镜像机连通异常')
    }
  } catch (e: any) {
    ElMessage.error(`探测失败：${e.message}`)
  } finally {
    mirrorLoading.value = false
  }
}

async function handleMirrorVersions() {
  if (!mirrorTarget.value?.mirror_url) return
  mirrorLoading.value = true
  try {
    const res = await mirrorVersions(mirrorTarget.value.mirror_url)
    if (res.versions) {
      mirrorVersionList.value = res.versions
      ElMessage.success(`查到 ${res.versions.length} 个可用版本`)
    } else {
      ElMessage.info('未查到版本信息')
    }
  } catch (e: any) {
    ElMessage.error(`查询失败：${e.message}`)
  } finally {
    mirrorLoading.value = false
  }
}

async function handleMirrorSwitchVersion() {
  if (!mirrorTarget.value?.mirror_url || !mirrorVersion.value) return
  mirrorLoading.value = true
  try {
    const res = await mirrorSwitchVersion(mirrorTarget.value.mirror_url, mirrorVersion.value)
    if (res.success) {
      ElMessage.success(`版本切换成功：${mirrorVersion.value}，请手动启动 ComfyUI`)
    } else {
      const needStop = res.needStop
      if (needStop) {
        ElMessage.warning('请先停止 ComfyUI 后再切换版本')
      } else {
        ElMessage.error(res.message || '切换失败')
      }
    }
  } catch (e: any) {
    ElMessage.error(`切换失败：${e.message}`)
  } finally {
    mirrorLoading.value = false
  }
}
</script>

<style scoped>
/* 继承 tool-page 样式 */
</style>