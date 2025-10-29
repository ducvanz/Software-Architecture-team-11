// src/components/RunPanel/RunPanel.jsx
import { useEffect, useRef, useState } from "react";
import { Button } from "antd";
import { startProcessApi, jobStatusApi, jobOutputsApi } from "../../api";
import JobStatusTable from "./JobStatusTable";
import PipelineFlow from "./PipelineFlow";
import "./RunPanel.css";

const RunPanel = ({ selectedImages, steps, onDone }) => {
  const [log, setLog] = useState("");
  const [running, setRunning] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [displayMap, setDisplayMap] = useState({}); // map hiển thị (đã xử lý sink)
  const timerRef = useRef(null);
  const wsRef = useRef(null); // websocket ref
  const historyRef = useRef({}); // { [filename]: [{state, current_filter, worker, ts}] }
  const lastLogCountRef = useRef(0); // <-- track logs consumed

  const append = (line) => setLog((x) => (x ? x + "\n" + line : line));

  const clearTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const closeWs = () => {
    try {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    } catch (e) {}
  };

  useEffect(() => {
    return () => {
      clearTimer();
      closeWs();
    };
  }, []);

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

  const formatLogEntry = (e) => {
    const ts = e.ts || "";
    const idx =
      e.stage_idx !== null && e.stage_idx !== undefined
        ? `#${e.stage_idx + 1}`
        : "";
    const stage = e.stage ? `stage:${e.stage}` : "";
    const worker = e.worker ? `worker:${e.worker}` : "";
    const file = e.file ? `${e.file}` : "";
    const level = e.level ? e.level.toUpperCase() : "INFO";
    return `[${ts}] [${level}] ${idx} ${stage} ${worker} ${file} - ${e.msg}`;
  };

  // process snapshot (from WS or poll)
  const handleSnapshot = async (st) => {
    const imgs = st.images || {};
    // lưu history + cập nhật display map
    for (const [name, snap] of Object.entries(imgs)) pushHistory(name, snap);
    recomputeDisplayMap(imgs);

    // append new logs (if any)
    const logs = Array.isArray(st.logs) ? st.logs : [];
    if (logs.length > lastLogCountRef.current) {
      const newLogs = logs.slice(lastLogCountRef.current);
      for (const l of newLogs) append(formatLogEntry(l));
      lastLogCountRef.current = logs.length;
    }

    // handle job completion
    if (st.status !== "running") {
      append(JSON.stringify(st));
      clearTimer();
      closeWs();

      if (st.status === "done") {
        try {
          const outs = await jobOutputsApi(st.job_id);
          append(`Outputs: ${outs.map((o) => o.name).join(", ")}`);
          onDone?.(outs);
        } catch (e) {
          // ignore
        }
      } else if (st.status === "error") {
        append(`Job error: ${st.error || "unknown"}`);
      }
      setRunning(false);
    }
  };

  const startPolling = (job_id) => {
    clearTimer();
    timerRef.current = setInterval(async () => {
      try {
        const st = await jobStatusApi(job_id);
        await handleSnapshot(st);
      } catch (e) {
        console.error("poll err", e);
        append("Poll lỗi, dừng polling.");
        clearTimer();
        setRunning(false);
      }
    }, 400);
  };

  const startWs = (job_id) => {
    try {
      closeWs();
      const loc = window.location;
      const wsProto = loc.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${wsProto}//${loc.host}/ws/jobs/${job_id}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        append("WS connected");
        // reset log counter to allow receiving all logs from beginning
        lastLogCountRef.current = 0;
      };

      ws.onmessage = async (ev) => {
        try {
          const st = JSON.parse(ev.data);
          // ignore not_found messages
          if (st.status === "not_found") return;
          await handleSnapshot(st);
        } catch (e) {
          console.error("ws parse err", e);
        }
      };

      ws.onerror = (e) => {
        console.warn("ws error", e);
      };

      ws.onclose = (ev) => {
        append("WS closed, fallback to polling");
        wsRef.current = null;
        // fallback to polling
        startPolling(job_id);
      };
    } catch (e) {
      console.error("startWs err", e);
      startPolling(job_id);
    }
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
    lastLogCountRef.current = 0;
    setRunning(true);
    append("Gửi job...");

    try {
      const { job_id } = await startProcessApi({
        images: selectedImages,
        steps,
      });
      setJobId(job_id);
      append(`Job: ${job_id}`);

      // try WebSocket first, fallback to polling
      startWs(job_id);
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

      {/* Flow visualization */}
      <PipelineFlow
        steps={steps || []}
        images={Array.isArray(selectedImages) ? selectedImages : []}
        stateMap={displayMap}
      />

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
