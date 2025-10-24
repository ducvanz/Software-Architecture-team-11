import { useEffect, useState } from "react";
import { API_BASE, listOutputs } from "../api";

export default function OutputsList({ externalOutputs }) {
  const [outputs, setOutputs] = useState([]);

  const refresh = async () => setOutputs(await listOutputs());
  useEffect(() => {
    refresh();
  }, []);
  useEffect(() => {
    if (externalOutputs?.length) refresh();
  }, [externalOutputs]);

  return (
    <section className="panel">
      <h2>4. Kết quả</h2>
      <button onClick={refresh}>Tải lại</button>
      <div className="grid">
        {outputs.map((o) => (
          <div className="card" key={o.name}>
            <div>{o.name}</div>
            <img src={`${API_BASE}${o.url}?v=${Date.now()}`} alt={o.name} />
          </div>
        ))}
      </div>
    </section>
  );
}
