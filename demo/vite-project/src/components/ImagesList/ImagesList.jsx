import { useEffect, useState } from "react";
import { API_BASE, listImagesApi, uploadFilesApi } from "../../api";
import { Button, Col, Row } from "antd";
import "./ImagesList.css";

const ImagesList = ({ selected, setSelected }) => {
  const [images, setImages] = useState([]);

  const refresh = async () => setImages(await listImagesApi());

  useEffect(() => {
    refresh();
  }, []);

  const onUpload = async (e) => {
    const files = e.target.files;
    if (!files?.length) {
      return;
    }

    await uploadFilesApi(files);
    await refresh();
    e.target.value = "";
  };

  const toggle = (name, checked) => {
    if (checked) {
      setSelected((prev) => [...new Set([...prev, name])]);
    } else {
      setSelected((prev) => prev.filter((x) => x !== name));
    }
  };

  return (
    <div className="images-list-container">
      <h2>1. Ảnh đầu vào</h2>
      <div>
        <input type="file" multiple accept="image/*" onChange={onUpload} />
        <Button
          type="primary"
          style={{ marginLeft: "20px" }}
          s
          onClick={refresh}
        >
          Tải lại danh sách
        </Button>
      </div>
      <div className="images-area">
        <Row gutter={[16, 24]}>
          {images.map((it) => (
            <Col span={6} key={it.name}>
              <div className="image-card">
                <div className="image-title">
                  <input
                    type="checkbox"
                    checked={selected.includes(it.name)}
                    onChange={(e) => toggle(it.name, e.target.checked)}
                  />
                  <div>{it.name}</div>
                </div>

                <div className="media">
                  <img
                    src={`${API_BASE}${it.url}?v=${Date.now()}`}
                    alt={it.name}
                  />
                </div>
              </div>
            </Col>
          ))}
        </Row>
      </div>
    </div>
  );
};

export default ImagesList;
