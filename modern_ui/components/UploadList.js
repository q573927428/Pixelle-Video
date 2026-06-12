const { defineComponent } = Vue;

const UploadList = defineComponent({
  name: "UploadList",
  props: ["uploads"],
  template: `
    <div class="upload-list">
      <div v-for="item in uploads" :key="item.path" class="upload-item">
        <span>{{ item.filename }} · {{ item.category }}</span>
        <el-button size="small" @click="window.open(item.url, '_blank')">预览</el-button>
      </div>
    </div>
  `
});

export default UploadList;