import { useEffect, useState } from "react";
import { listFiltersApi } from "../../api";
import { Button, Input, Typography } from "antd";
import "./FiltersPanel.css";

const { Text } = Typography;
const { TextArea } = Input;

const FiltersPanel = ({ steps, setSteps }) => {
  const [filters, setFilters] = useState([]);
  const [name, setName] = useState("");
  const [params, setParams] = useState("{}");
  const [paramErr, setParamErr] = useState(null);

  const refresh = async () => setFilters(await listFiltersApi());

  useEffect(() => {
    refresh();
  }, []);

  const onParamsChange = (v) => {
    setParams(v);
    try {
      JSON.parse(v);
      setParamErr(null);
    } catch (e) {
      setParamErr(e.message);
    }
  };

  const formatParams = () => {
    try {
      const pretty = JSON.stringify(JSON.parse(params), null, 2);
      setParams(pretty);
      setParamErr(null);
    } catch (e) {
      setParamErr(e.message);
    }
  };

  const addStep = () => {
    if (!name) {
      return alert("Chọn tên filter");
    }

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
    setParamErr(null);
  };

  const removeStep = (i) =>
    setSteps((prev) => prev.filter((_, idx) => idx !== i));

  const exampleParams = (schema) => {
    if (!schema || !Object.keys(schema).length) {
      return "{}";
    }

    const obj = {};
    for (const [k, v] of Object.entries(schema)) {
      obj[k] = v.default ?? (v.type === "int" || v.type === "float" ? 0 : "");
    }
    return JSON.stringify(obj, null, 2);
  };

  return (
    <div className="filters-panel-container">
      <h2>2. Chọn filter & tham số</h2>

      <Button type="primary" style={{ width: "fit-content" }} onClick={refresh}>
        Tải lại filters
      </Button>

      <div className="filters-list">
        {filters.map((f) => (
          <div className="filter-card" key={f.name}>
            <h4>{f.name}</h4>

            <div className="params-block">
              <div className="params-title">Params</div>
              {f.params && Object.keys(f.params).length ? (
                <div className="json">{JSON.stringify(f.params, null, 2)}</div>
              ) : (
                <span className="params-none">(none)</span>
              )}
            </div>

            <div>
              <Button
                style={{ marginTop: 10 }}
                onClick={() => {
                  setName(f.name);
                  setParams(exampleParams(f.params));
                  setParamErr(null);
                }}
              >
                Chọn
              </Button>
            </div>
          </div>
        ))}
      </div>

      <h3>Pipeline hiện tại</h3>

      <div className="pipeline-row">
        <Input
          placeholder="Tên filter"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="filter-name"
        />

        <div className="json-editor-wrap">
          <TextArea
            value={params}
            onChange={(e) => onParamsChange(e.target.value)}
            placeholder='JSON params, ví dụ {"scale":0.5}'
            autoSize={{ minRows: 3, maxRows: 10 }}
            allowClear
            className="json-editor"
          />
          <div className="json-editor-actions">
            <Button size="small" onClick={formatParams}>
              Format JSON
            </Button>
            {paramErr ? (
              <Text type="danger" className="json-error">
                JSON lỗi: {paramErr}
              </Text>
            ) : (
              <Text type="secondary" className="json-ok">
                JSON hợp lệ
              </Text>
            )}
          </div>
        </div>

        <Button type="primary" onClick={addStep} disabled={!name || !!paramErr}>
          Thêm bước
        </Button>
        <Button danger onClick={() => setSteps([])}>
          Xoá hết
        </Button>
      </div>

      <ol>
        {steps.map((s, i) => (
          <li key={i}>
            <code>{s.name}</code> {JSON.stringify(s.params)}{" "}
            <button
              className="remove-filter-button"
              onClick={() => removeStep(i)}
            >
              x
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
};

export default FiltersPanel;
