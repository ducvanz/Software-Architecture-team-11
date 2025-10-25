import axios from "axios";

// đổi nếu backend khác host/port
const API_BASE = "http://127.0.0.1:8000";

const listFiltersApi = async () =>
  (await axios.get(`${API_BASE}/api/filters`)).data;
const listImagesApi = async () =>
  (await axios.get(`${API_BASE}/api/images`)).data.images || [];
const listOutputsApi = async () =>
  (await axios.get(`${API_BASE}/api/outputs`)).data.outputs || [];

const uploadFilesApi = async (files) => {
  const form = new FormData();
  for (const f of files) {
    form.append("files", f);
  }

  return (await axios.post(`${API_BASE}/api/upload`, form)).data;
};

const startProcessApi = async (payload) =>
  (await axios.post(`${API_BASE}/api/process`, payload)).data; // {job_id, status}
const jobStatusApi = async (jobId) =>
  (await axios.get(`${API_BASE}/api/jobs/${jobId}/status`)).data;
const jobOutputsApi = async (jobId) =>
  (await axios.get(`${API_BASE}/api/jobs/${jobId}/outputs`)).data.outputs || [];

export {
  API_BASE,
  listFiltersApi,
  listImagesApi,
  listOutputsApi,
  uploadFilesApi,
  startProcessApi,
  jobStatusApi,
  jobOutputsApi,
};
