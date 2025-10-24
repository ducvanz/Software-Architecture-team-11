import { useState } from "react";
import { startProcess, jobStatus, jobOutputs } from "../api";

export default function RunPanel({ selectedImages, steps, onDone }) {
  const [log, setLog] = useState("");

  const append = (line) => setLog((x) => (x ? x + "\n" + line : line));

  const run = async () => {
    if (!selectedImages.length) return alert("Chọn ít nhất 1 ảnh");
    if (!steps.length) return alert("Thêm ít nhất 1 bước");
    setLog("");
    append("Gửi job...");

    try {
      const { job_id } = await startProcess({ images: selectedImages, steps });
      append(`Job: ${job_id}`);

      // poll nhanh tới khi không còn "running"
      let status = null;
      do {
        await new Promise((r) => setTimeout(r, 700));
        status = await jobStatus(job_id);
        append(JSON.stringify(status));
      } while (status.status === "running");

      const outs = await jobOutputs(job_id);
      append(`Outputs: ${outs.map((o) => o.name).join(", ")}`);
      onDone?.(outs);
    } catch (e) {
      console.error(e);
      append("Có lỗi khi chạy pipeline (xem console).");
    }
  };

  return (
    <section className="panel">
      <h2>3. Chạy pipeline</h2>
      <button onClick={run}>Run</button>
      <pre>{log}</pre>
    </section>
  );
}
