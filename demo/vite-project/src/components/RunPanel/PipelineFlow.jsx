import React from "react";
import "./PipelineFlow.css";

/**
 * PipelineFlow
 * props:
 *  - steps: [{ name, params }, ...]
 *  - images: [filename, ...]
 *  - stateMap: { filename: { state, current_filter, worker } }
 */
const PipelineFlow = ({ steps = [], images = [], stateMap = {} }) => {
  const cols = ["loader", ...steps.map((s) => s.name), "sink"];

  const itemsByCol = {};
  cols.forEach((c) => (itemsByCol[c] = []));

  for (const name of images) {
    const snap = stateMap[name] || {};
    let col = "loader";
    if (snap.state === "done") col = "sink";
    else if (snap.current_filter) col = snap.current_filter;
    itemsByCol[col].push({ name, snap });
  }

  const getProcessingCount = (colName) =>
    (itemsByCol[colName] || []).filter((it) => it.snap.state === "processing").length;

  return (
    <div className="pipeline-flow" role="presentation">
      {cols.map((col) => (
        <div className="pf-col" key={col}>
          <div className="pf-col-header">
            <div className="pf-col-title">
              {col === "loader" ? "Loader" : col === "sink" ? "Sink" : col}
            </div>
            <div className="pf-col-meta">
              <span className="pf-count">{itemsByCol[col].length}</span>
              <span className="pf-workers"> / active: {getProcessingCount(col)}</span>
            </div>
          </div>

          <div className="pf-col-body">
            {(itemsByCol[col] || []).map((it) => (
              <div
                key={it.name}
                className={"pf-item " + (it.snap.state === "processing" ? "pf-item-active" : "")}
                title={`${it.name} — ${it.snap.state || "—"}${it.snap.worker ? " @ " + it.snap.worker : ""}`}
              >
                <div className="pf-item-thumb">{it.name.split(".")[0]}</div>
                <div className="pf-item-info">
                  <div className="pf-item-name">{it.name}</div>
                  <div className="pf-item-state">{it.snap.state || "—"}</div>
                </div>
              </div>
            ))}

            {(!itemsByCol[col] || itemsByCol[col].length === 0) && <div className="pf-empty">—</div>}
          </div>
        </div>
      ))}
    </div>
  );
};

export default PipelineFlow;