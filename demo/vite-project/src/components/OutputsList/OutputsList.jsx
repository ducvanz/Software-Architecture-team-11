import { useEffect, useState } from "react";
import { API_BASE, listOutputsApi } from "../../api";
import { Button, Col, Row } from "antd";
import "./OutputsList.css";

const OutputsList = ({ externalOutputs }) => {
  const [outputs, setOutputs] = useState([]);

  const refresh = async () => setOutputs(await listOutputsApi());

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    if (externalOutputs?.length) {
      refresh();
    }
  }, [externalOutputs]);

  return (
    <div className="outputs-list-container">
      <h2>4. Kết quả</h2>
      <Button type="primary" style={{ width: "fit-content" }} onClick={refresh}>
        Tải lại
      </Button>
      <div className="output-images-area">
        <Row gutter={[16, 24]}>
          {outputs.map((o) => (
            <Col span={6} key={o.name}>
              <div className="output-image-card">
                <div className="output-image-title">{o.name}</div>
                <div className="output-image-wrapper">
                  <img
                    src={`${API_BASE}${o.url}?v=${Date.now()}`}
                    alt={o.name}
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

export default OutputsList;
