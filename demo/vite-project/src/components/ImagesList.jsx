import { useEffect, useState } from "react";
import { API_BASE, listImages, uploadFiles } from "../api";

export default function ImagesList({ selected, setSelected }) {
  const [images, setImages] = useState([]);

  const refresh = async () => setImages(await listImages());

  useEffect(() => {
    refresh();
  }, []);

  const onUpload = async (e) => {
    const files = e.target.files;
    if (!files?.length) return;
    await uploadFiles(files);
    await refresh();
    e.target.value = "";
  };

  const toggle = (name, checked) => {
    if (checked) setSelected((prev) => [...new Set([...prev, name])]);
    else setSelected((prev) => prev.filter((x) => x !== name));
  };

  return (
    <section className="panel">
      <h2>1. Ảnh đầu vào</h2>
      <div className="row">
        <input type="file" multiple accept="image/*" onChange={onUpload} />
        <button onClick={refresh}>Tải lại danh sách</button>
      </div>
      <div className="grid">
        {images.map((it) => (
          <label className="card" key={it.name}>
            <div className="row">
              <input
                type="checkbox"
                checked={selected.includes(it.name)}
                onChange={(e) => toggle(it.name, e.target.checked)}
              />
              <span>{it.name}</span>
            </div>
            <img src={`${API_BASE}${it.url}?v=${Date.now()}`} alt={it.name} />
          </label>
        ))}
      </div>
    </section>
  );
}
