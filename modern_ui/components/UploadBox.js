const { h, defineComponent } = Vue;

const UploadBox = defineComponent({
  name: "UploadBox",
  props: ["category"],
  emits: ["upload", "select-history"],
  template: `
    <div class="upload-box-row">
      <el-upload class="compact-upload" drag multiple :auto-upload="false" :show-file-list="false" :on-change="file => $emit('upload', file.raw, category)">
        <div class="compact-upload-content">
          <span class="compact-upload-icon">＋</span>
          <span>上传文件</span>
          <span class="compact-upload-hint">点击或拖拽</span>
        </div>
      </el-upload>
      <el-button size="small" class="history-btn" @click="$emit('select-history', category)">
        <span style="margin-right:4px;">📂</span> 从历史选择
      </el-button>
    </div>
  `
});

export default UploadBox;