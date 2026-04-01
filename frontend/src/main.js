import ArcoVue from "@arco-design/web-vue";
import { createPinia } from "pinia";
import { createApp } from "vue";
import App from "./App.vue";
import i18n from "./i18n";
import router from "./router";
import "./style.css";
import "@arco-design/web-vue/dist/arco.css";

const app = createApp(App);

app.use(createPinia());
app.use(ArcoVue);
app.use(router);
app.use(i18n);

app.mount("#app");
