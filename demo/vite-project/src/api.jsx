import axios from "axios";

// đổi nếu backend khác host/port
export const API_BASE = "http://127.0.0.1:8000";

export const listFilters = async () =>
  (await axios.get(`${API_BASE}/api/filters`)).data;
export const listImages = async () =>
  (await axios.get(`${API_BASE}/api/images`)).data.images || [];
export const listOutputs = async () =>
  (await axios.get(`${API_BASE}/api/outputs`)).data.outputs || [];

export const uploadFiles = async (files) => {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  return (await axios.post(`${API_BASE}/api/upload`, form)).data;
};

export const startProcess = async (payload) =>
  (await axios.post(`${API_BASE}/api/process`, payload)).data; // {job_id, status}
export const jobStatus = async (jobId) =>
  (await axios.get(`${API_BASE}/api/jobs/${jobId}/status`)).data;
export const jobOutputs = async (jobId) =>
  (await axios.get(`${API_BASE}/api/jobs/${jobId}/outputs`)).data.outputs || [];
