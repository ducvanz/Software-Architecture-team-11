// src/components/RunPanel/RunPanel.jsx
import { useEffect, useRef, useState } from "react";
import { Button } from "antd";
import { startProcessApi, jobStatusApi, jobOutputsApi } from "../../api";
import JobStatusTable from "./JobStatusTable";
import "./RunPanel.css";

const RunPanel = ({ selectedImages, steps, onDone }) => {
  const [log, setLog] = useState("");
  const [running, setRunning] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [displayMap, setDisplayMap] = useState({}); // map hiển thị (đã xử lý sink)
  const timerRef = useRef(null);
  const historyRef = useRef({}); // { [filename]: [{state, current_filter, worker, ts}] }

  const append = (line) => setLog((x) => (x ? x + "\n" + line : line));

  const clearTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  useEffect(() => () => clearTimer(), []);

  // === history helpers ===
  const pushHistory = (name, snap) => {
    const now = Date.now();
    if (!historyRef.current[name]) historyRef.current[name] = [];
    const arr = historyRef.current[name];
    const last = arr[arr.length - 1];
    const changed =
      !last ||
      last.state !== snap.state ||
      last.current_filter !== snap.current_filter ||
      last.worker !== snap.worker;
    if (changed) arr.push({ ...snap, ts: now });
  };

  const lastNonSink = (name) => {
    const arr = historyRef.current[name] || [];
    for (let i = arr.length - 1; i >= 0; i--) {
      if (arr[i].worker && arr[i].worker !== "sink") return arr[i];
    }
    return null;
  };

  const recomputeDisplayMap = (snapImages) => {
    const out = {};
    for (const name of Object.keys(snapImages)) {
      const s = snapImages[name] || {};
      let current_filter = s.current_filter ?? "—";
      let worker = s.worker ?? "—";

      if (s.state === "done") {
        const prev = lastNonSink(name);
        if (prev) {
          current_filter = prev.current_filter ?? current_filter;
          worker = prev.worker ?? worker;
        }
      }
      out[name] = { state: s.state, current_filter, worker };
    }
    setDisplayMap(out);
  };

  const run = async () => {
    if (!Array.isArray(selectedImages) || selectedImages.length === 0)
      return alert("Chọn ít nhất 1 ảnh");
    if (!Array.isArray(steps) || steps.length === 0)
      return alert("Thêm ít nhất 1 bước");

    setLog("");
    setDisplayMap({});
    setJobId(null);
    historyRef.current = {};
    setRunning(true);
    append("Gửi job...");

    try {
      const { job_id } = await startProcessApi({
        images: selectedImages,
        steps,
      });
      setJobId(job_id);
      append(`Job: ${job_id}`);

      // Poll nhanh để bắt processing
      timerRef.current = setInterval(async () => {
        try {
          const st = await jobStatusApi(job_id);

          // lưu history + cập nhật display map
          const imgs = st.images || {};
          for (const [name, snap] of Object.entries(imgs))
            pushHistory(name, snap);
          recomputeDisplayMap(imgs);

          if (st.status !== "running") {
            append(JSON.stringify(st));
            clearTimer();

            if (st.status === "done") {
              const outs = await jobOutputsApi(job_id);
              append(`Outputs: ${outs.map((o) => o.name).join(", ")}`);
              onDone?.(outs);
            } else if (st.status === "error") {
              append(`Job error: ${st.error || "unknown"}`);
            }
            setRunning(false);
          }
        } catch (e) {
          console.error(e);
          append("Poll lỗi, dừng.");
          clearTimer();
          setRunning(false);
        }
      }, 300);
    } catch (e) {
      console.error(e);
      append("Có lỗi khi chạy pipeline (xem console).");
      setRunning(false);
    }
  };

  return (
    <div className="run-panel-container">
      <h2>3. Chạy pipeline</h2>
      <div className="run-actions">
        <Button type="primary" onClick={run} disabled={running}>
          {running ? "Running..." : "Run"}
        </Button>
        {jobId && <small className="job-id">Job: {jobId}</small>}
      </div>

      {/* Bảng tiến trình (cột = filter; hàng = ảnh; gồm Status + Worker) */}
      <JobStatusTable
        images={Array.isArray(selectedImages) ? selectedImages : []}
        steps={Array.isArray(steps) ? steps : []}
        stateMap={displayMap}
      />

      <h4>Log</h4>
      <pre className="log-area">{log}</pre>
    </div>
  );
};

export default RunPanel;
