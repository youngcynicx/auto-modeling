import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";

const ACTIVE_STATUSES = new Set(["queued", "generating", "exporting", "validating"]);
const STATUS_LABELS = {
  queued: "等待建模",
  generating: "正在生成模型脚本",
  exporting: "正在导出 STEP / STL",
  validating: "正在校验模型",
  ready: "模型已完成",
  failed: "本次生成失败",
};

const dom = {
  form: document.querySelector("#prompt-form"),
  input: document.querySelector("#prompt-input"),
  label: document.querySelector("#prompt-label"),
  submit: document.querySelector("#submit-button"),
  newJob: document.querySelector("#new-job-button"),
  messages: document.querySelector("#messages"),
  version: document.querySelector("#version-badge"),
  status: document.querySelector("#job-status"),
  statusDot: document.querySelector("#status-dot"),
  empty: document.querySelector("#empty-state"),
  loading: document.querySelector("#loading-state"),
  loadingTitle: document.querySelector("#loading-title"),
  loadingDetail: document.querySelector("#loading-detail"),
  previewTitle: document.querySelector("#preview-title"),
  downloads: document.querySelector("#download-actions"),
  downloadStep: document.querySelector("#download-step"),
  downloadStl: document.querySelector("#download-stl"),
  modelSize: document.querySelector("#model-size"),
  solidCount: document.querySelector("#solid-count"),
  viewport: document.querySelector("#viewport"),
  canvas: document.querySelector("#model-canvas"),
  toast: document.querySelector("#toast"),
};

const state = {
  jobId: localStorage.getItem("auto-modeling-job"),
  job: null,
  loadedRevision: null,
  pollTimer: null,
  toastTimer: null,
};

let renderer;
let scene;
let camera;
let controls;
let modelMesh;
let grid;

function initViewer() {
  renderer = new THREE.WebGLRenderer({ canvas: dom.canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100000);
  camera.up.set(0, 0, 1);
  camera.position.set(80, -100, 70);

  controls = new OrbitControls(camera, dom.canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.07;
  controls.screenSpacePanning = true;

  const hemisphere = new THREE.HemisphereLight(0xffffff, 0x777164, 2.4);
  scene.add(hemisphere);
  const key = new THREE.DirectionalLight(0xffffff, 3.2);
  key.position.set(70, -100, 120);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xdce8ff, 1.35);
  fill.position.set(-80, 40, 30);
  scene.add(fill);

  const resizeObserver = new ResizeObserver(resizeViewer);
  resizeObserver.observe(dom.viewport);
  renderer.setAnimationLoop(() => {
    controls.update();
    renderer.render(scene, camera);
  });
}

function resizeViewer() {
  const width = dom.viewport.clientWidth;
  const height = dom.viewport.clientHeight;
  if (!width || !height) return;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

function clearModel() {
  if (modelMesh) {
    scene.remove(modelMesh);
    modelMesh.geometry.dispose();
    modelMesh.material.dispose();
    modelMesh = null;
  }
  if (grid) {
    scene.remove(grid);
    grid.geometry.dispose();
    grid.material.dispose();
    grid = null;
  }
  state.loadedRevision = null;
}

function loadModel(job, revision) {
  const item = job.revisions.find((entry) => entry.number === revision);
  if (!item?.artifacts?.stl || state.loadedRevision === revision) return;
  const loader = new STLLoader();
  dom.empty.hidden = true;
  dom.loading.hidden = false;
  dom.loadingTitle.textContent = "正在载入三维预览";
  dom.loadingDetail.textContent = `正在准备 V${revision} 的 STL 网格。`;

  loader.load(
    `${item.artifacts.stl}?cache=${encodeURIComponent(item.updated_at)}`,
    (geometry) => {
      clearModel();
      geometry.computeVertexNormals();
      geometry.computeBoundingBox();
      const center = new THREE.Vector3();
      geometry.boundingBox.getCenter(center);
      geometry.translate(-center.x, -center.y, -center.z);
      geometry.computeBoundingSphere();

      const material = new THREE.MeshStandardMaterial({
        color: 0xd76543,
        metalness: 0.08,
        roughness: 0.62,
      });
      modelMesh = new THREE.Mesh(geometry, material);
      modelMesh.castShadow = true;
      modelMesh.receiveShadow = true;
      scene.add(modelMesh);

      const radius = Math.max(geometry.boundingSphere.radius, 1);
      grid = new THREE.GridHelper(radius * 4.5, 18, 0xaaa69c, 0xc9c6bd);
      grid.rotation.x = Math.PI / 2;
      grid.position.z = -radius * 1.05;
      grid.material.transparent = true;
      grid.material.opacity = 0.38;
      scene.add(grid);

      controls.target.set(0, 0, 0);
      camera.near = Math.max(radius / 1000, 0.01);
      camera.far = radius * 100;
      camera.position.set(radius * 1.55, -radius * 1.85, radius * 1.25);
      camera.updateProjectionMatrix();
      controls.update();
      state.loadedRevision = revision;
      dom.loading.hidden = true;
      dom.empty.hidden = true;
    },
    undefined,
    () => {
      dom.loading.hidden = true;
      dom.empty.hidden = false;
      dom.empty.querySelector("h3").textContent = "预览加载失败";
      dom.empty.querySelector("p").textContent = "模型已经生成，但浏览器未能读取 STL 文件。";
      showToast("STL 预览加载失败，请刷新页面重试。", true);
    },
  );
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `请求失败（${response.status}）`);
  return data;
}

async function submitPrompt(event) {
  event.preventDefault();
  const prompt = dom.input.value.trim();
  if (prompt.length < 3) {
    showToast("请先输入更完整的建模需求。", true);
    return;
  }

  setBusy(true);
  try {
    const canEdit = state.jobId && state.job?.current_revision;
    const path = canEdit ? `/api/jobs/${state.jobId}/revisions` : "/api/jobs";
    const job = await api(path, { method: "POST", body: JSON.stringify({ prompt }) });
    state.jobId = job.id;
    state.job = job;
    localStorage.setItem("auto-modeling-job", job.id);
    dom.input.value = "";
    renderJob(job);
    schedulePoll(250);
  } catch (error) {
    showToast(error.message, true);
  } finally {
    if (!ACTIVE_STATUSES.has(state.job?.status)) setBusy(false);
  }
}

async function fetchJob() {
  if (!state.jobId) return;
  try {
    const job = await api(`/api/jobs/${state.jobId}`);
    state.job = job;
    renderJob(job);
    if (ACTIVE_STATUSES.has(job.status)) schedulePoll(1000);
  } catch (error) {
    if (error.message.includes("不存在")) resetJob();
    else {
      showToast(error.message, true);
      schedulePoll(2500);
    }
  }
}

function schedulePoll(delay) {
  window.clearTimeout(state.pollTimer);
  state.pollTimer = window.setTimeout(fetchJob, delay);
}

function renderJob(job) {
  const active = ACTIVE_STATUSES.has(job.status);
  const displayRevision = job.current_revision || job.pending_revision;
  dom.status.textContent = STATUS_LABELS[job.status] || job.status;
  dom.version.textContent = displayRevision ? `V${displayRevision}` : "未生成";
  dom.previewTitle.textContent = displayRevision ? `模型预览 · V${displayRevision}` : "模型预览";
  dom.statusDot.className = `status-dot ${active ? "active" : job.status}`;
  setBusy(active);
  renderMessages(job.messages);

  dom.loading.hidden = !active;
  if (active) {
    dom.empty.hidden = true;
    dom.loadingTitle.textContent = STATUS_LABELS[job.status] || "正在处理";
    dom.loadingDetail.textContent = "模型生成和几何校验通常需要几分钟，请保持页面打开。";
  }

  const current = job.revisions.find((item) => item.number === job.current_revision);
  if (current?.status === "ready") {
    dom.downloads.hidden = false;
    dom.downloadStep.href = current.artifacts.step;
    dom.downloadStl.href = current.artifacts.stl;
    dom.modelSize.hidden = false;
    dom.solidCount.hidden = false;
    const box = current.validation.bounding_box_mm;
    dom.modelSize.querySelector("strong").textContent = `${box.x} × ${box.y} × ${box.z} mm`;
    dom.solidCount.querySelector("strong").textContent = `${current.validation.solid_count}`;
    loadModel(job, job.current_revision);
  } else if (!active && !modelMesh) {
    dom.empty.hidden = false;
    dom.loading.hidden = true;
  }

  if (job.status === "failed") {
    dom.loading.hidden = true;
    if (!job.current_revision) dom.empty.hidden = false;
  }

  dom.label.textContent = job.current_revision ? "自然语言修改需求" : "自然语言建模需求";
  dom.input.placeholder = job.current_revision
    ? "例如：把四个安装孔改为直径 6 mm，并将板厚增加到 8 mm。"
    : "例如：创建一个 80 × 40 × 6 mm 的安装板，四角各有一个直径 5 mm 的通孔。";
  dom.submit.querySelector("span").textContent = job.current_revision ? "提交修改" : "生成模型";
}

function renderMessages(messages) {
  const welcome = `
    <article class="message message-assistant welcome-message">
      <span class="message-author">建模助手</span>
      <p>告诉我零件用途、关键尺寸、孔位或接口。我会生成参数化模型，完成后你可以继续用自然语言修改。</p>
    </article>`;
  dom.messages.innerHTML = welcome;
  for (const message of messages) {
    const article = document.createElement("article");
    article.className = `message message-${message.role}${message.kind === "error" ? " message-error" : ""}`;
    const author = document.createElement("span");
    author.className = "message-author";
    author.textContent = message.role === "user" ? `你的需求 · V${message.revision}` : `建模助手 · V${message.revision}`;
    const text = document.createElement("p");
    text.textContent = message.text;
    article.append(author, text);
    dom.messages.append(article);
  }
  dom.messages.scrollTop = dom.messages.scrollHeight;
}

function setBusy(busy) {
  dom.input.disabled = busy;
  dom.submit.disabled = busy;
  dom.newJob.disabled = busy;
}

function resetJob() {
  window.clearTimeout(state.pollTimer);
  state.jobId = null;
  state.job = null;
  localStorage.removeItem("auto-modeling-job");
  clearModel();
  dom.form.reset();
  dom.status.textContent = "等待需求";
  dom.statusDot.className = "status-dot";
  dom.version.textContent = "未生成";
  dom.previewTitle.textContent = "模型预览";
  dom.downloads.hidden = true;
  dom.modelSize.hidden = true;
  dom.solidCount.hidden = true;
  dom.loading.hidden = true;
  dom.empty.hidden = false;
  dom.empty.querySelector("h3").textContent = "等待第一个模型";
  dom.empty.querySelector("p").textContent = "提交左侧需求后，STL 预览会出现在这里。";
  renderMessages([]);
  dom.label.textContent = "自然语言建模需求";
  dom.submit.querySelector("span").textContent = "生成模型";
  setBusy(false);
}

function showToast(message, isError = false) {
  window.clearTimeout(state.toastTimer);
  dom.toast.textContent = message;
  dom.toast.style.background = isError ? "#86351f" : "#302f2c";
  dom.toast.hidden = false;
  state.toastTimer = window.setTimeout(() => { dom.toast.hidden = true; }, 4200);
}

dom.form.addEventListener("submit", submitPrompt);
dom.newJob.addEventListener("click", resetJob);
dom.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
    event.preventDefault();
    dom.form.requestSubmit();
  }
});

initViewer();
if (state.jobId) fetchJob();
