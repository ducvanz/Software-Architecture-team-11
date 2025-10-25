import { useState } from "react";
import { startProcessApi, jobStatusApi, jobOutputsApi } from "../../api";
import { Button } from "antd";
import "./RunPanel.css";

const RunPanel = ({ selectedImages, steps, onDone }) => {
  const [log, setLog] = useState("");

  const append = (line) => setLog((x) => (x ? x + "\n" + line : line));

  const run = async () => {
    if (!selectedImages.length) {
      return alert("Chọn ít nhất 1 ảnh");
    }

    if (!steps.length) {
      return alert("Thêm ít nhất 1 bước");
    }

    setLog("");
    append("Gửi job...");

    try {
      const { job_id } = await startProcessApi({
        images: selectedImages,
        steps,
      });
      append(`Job: ${job_id}`);

      // poll nhanh tới khi không còn "running"
      let status = null;
      do {
        await new Promise((r) => setTimeout(r, 700));
        status = await jobStatusApi(job_id);
        append(JSON.stringify(status));
      } while (status.status === "running");

      const outs = await jobOutputsApi(job_id);
      append(`Outputs: ${outs.map((o) => o.name).join(", ")}`);
      onDone?.(outs);
    } catch (e) {
      console.error(e);
      append("Có lỗi khi chạy pipeline (xem console).");
    }
  };

  return (
    <div className="run-panel-container">
      <h2>3. Chạy pipeline</h2>
      <Button type="primary" style={{ width: "fit-content" }} onClick={run}>
        Run
      </Button>
      <pre className="log-area">{log}</pre>
    </div>
  );
};

export default RunPanel;
