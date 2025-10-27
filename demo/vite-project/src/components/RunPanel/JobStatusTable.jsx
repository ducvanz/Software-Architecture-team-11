import React, { useMemo } from "react";

export default function JobStatusTable({
  images = [],
  steps = [],
  stateMap = {},
}) {
  const imgs = Array.isArray(images) ? images : [];

  // Tạo danh sách tên filter an toàn (bỏ rỗng & trùng)
  const stepNames = useMemo(() => {
    const stepsSafe = Array.isArray(steps) ? steps : [];
    const raw = stepsSafe
      .map((s) => (s && s.name ? String(s.name) : ""))
      .filter(Boolean);
    return Array.from(new Set(raw));
  }, [steps]);

  const badgeClass = (state) => {
    if (state === "done") return "badge done";
    if (state === "processing") return "badge processing";
    if (state === "queued") return "badge queued";
    if (state === "error") return "badge error";
    return "badge";
  };

  // Tính trạng thái & worker cho 1 ô (ảnh, filter)
  const cellInfo = (imgName, stepName) => {
    const snap = (stateMap && stateMap[imgName]) || {}; // {state, current_filter, worker}
    const overall = snap.state || "queued";

    if (overall === "error")
      return { status: "error", worker: snap.worker || "—" };
    if (overall === "done") return { status: "done", worker: "—" };

    const cur = snap.current_filter || null;
    if (!cur) return { status: "queued", worker: "—" };

    const curIdx = stepNames.indexOf(cur);
    const idx = stepNames.indexOf(stepName);
    if (idx < 0 || curIdx < 0) return { status: "—", worker: "—" };
    if (idx < curIdx) return { status: "done", worker: "—" };
    if (idx === curIdx)
      return { status: "processing", worker: snap.worker || "—" };
    return { status: "queued", worker: "—" };
  };

  if (stepNames.length === 0) return null;

  return (
    <div className="status-wrap">
      <table className="status-table">
        <thead>
          <tr>
            <th rowSpan={2} className="sticky-left">
              Image
            </th>
            {stepNames.map((sn, i) => (
              <th key={`${sn}-${i}`} colSpan={2} className="group-head">
                {sn}
              </th>
            ))}
          </tr>
          <tr className="subhead">
            {stepNames.map((sn, i) => (
              <React.Fragment key={`sub-${sn}-${i}`}>
                <th>Status</th>
                <th>Worker</th>
              </React.Fragment>
            ))}
          </tr>
        </thead>
        <tbody>
          {imgs.map((img) => (
            <tr key={img}>
              <th className="sticky-left">{img}</th>
              {stepNames.map((sn, i) => {
                const { status, worker } = cellInfo(img, sn);
                return (
                  <React.Fragment key={`${img}-${sn}-${i}`}>
                    <td className="td-status">
                      <span className={badgeClass(status)}>{status}</span>
                    </td>
                    <td className="td-worker">{worker}</td>
                  </React.Fragment>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
