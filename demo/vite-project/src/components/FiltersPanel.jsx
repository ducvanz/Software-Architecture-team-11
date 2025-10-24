import { useEffect, useState } from "react";
import { listFilters } from "../api";

export default function FiltersPanel({ steps, setSteps }) {
  const [filters, setFilters] = useState([]);
  const [name, setName] = useState("");
  const [params, setParams] = useState("{}");

  const refresh = async () => setFilters(await listFilters());
  useEffect(() => {
    refresh();
  }, []);

  const addStep = () => {
    if (!name) return alert("Chọn tên filter");
    let p = {};
    if (params.trim()) {
      try {
        p = JSON.parse(params);
      } catch {
        return alert("Params phải là JSON hợp lệ");
      }
    }
    setSteps((prev) => [...prev, { name, params: p }]);
    setName("");
    setParams("{}");
  };

  const removeStep = (i) =>
    setSteps((prev) => prev.filter((_, idx) => idx !== i));

  const exampleParams = (schema) => {
    if (!schema || !Object.keys(schema).length) return "{}";
    const obj = {};
    for (const [k, v] of Object.entries(schema)) {
      obj[k] = v.default ?? (v.type === "int" || v.type === "float" ? 0 : "");
    }
    return JSON.stringify(obj);
  };

  return (
    <section className="panel">
      <h2>2. Chọn filter & tham số</h2>
      <button onClick={refresh}>Tải lại filters</button>
      <div className="grid">
        {filters.map((f) => (
          <div className="card" key={f.name}>
            <h4>{f.name}</h4>
            <small>
              Params:{" "}
              {Object.keys(f.params || {}).length
                ? JSON.stringify(f.params)
                : "(none)"}
            </small>
            <div>
              <button
                onClick={() => {
                  setName(f.name);
                  setParams(exampleParams(f.params));
                }}
              >
                Chọn
              </button>
            </div>
          </div>
        ))}
      </div>

      <h3>Pipeline hiện tại</h3>
      <div className="row">
        <input
          placeholder="Tên filter"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          placeholder='JSON params, ví dụ {"scale":0.5}'
          value={params}
          onChange={(e) => setParams(e.target.value)}
        />
        <button onClick={addStep}>Thêm bước</button>
        <button onClick={() => setSteps([])}>Xoá hết</button>
      </div>
      <ol>
        {steps.map((s, i) => (
          <li key={i}>
            <code>{s.name}</code> {JSON.stringify(s.params)}{" "}
            <button onClick={() => removeStep(i)}>x</button>
          </li>
        ))}
      </ol>
    </section>
  );
}
