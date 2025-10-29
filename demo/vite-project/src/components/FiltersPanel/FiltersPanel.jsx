import { useEffect, useState } from "react";
import { listFiltersApi } from "../../api";
import { Button, Input, Typography, Select, InputNumber, Switch, Space } from "antd";
import "./FiltersPanel.css";

const { Text } = Typography;
const { TextArea } = Input;

const FiltersPanel = ({ steps, setSteps }) => {
  const [filters, setFilters] = useState([]);
  const [name, setName] = useState("");
  // params as object for form-driven editing
  const [paramsObj, setParamsObj] = useState({});
  const [schema, setSchema] = useState({});

  const refresh = async () => setFilters(await listFiltersApi());

  useEffect(() => {
    refresh();
  }, []);

  const initParamsFromSchema = (s) => {
    if (!s || !Object.keys(s).length) return {};
    const obj = {};
    for (const [k, v] of Object.entries(s)) {
      if (v.default !== undefined && v.default !== null) {
        obj[k] = v.default;
      } else if (v.type === "int" || v.type === "float") {
        obj[k] = null;
      } else if (v.type === "enum") {
        obj[k] = (v.options && v.options[0]) || "";
      } else if (v.type === "boolean") {
        obj[k] = false;
      } else {
        obj[k] = "";
      }
    }
    return obj;
  };

  const onSelectFilterFromList = (f) => {
    setName(f.name);
    const s = f.params || {};
    setSchema(s);
    setParamsObj(initParamsFromSchema(s));
  };

  const onNameChange = (v) => {
    setName(v);
    const match = filters.find((f) => f.name === v);
    if (match) {
      setSchema(match.params || {});
      setParamsObj(initParamsFromSchema(match.params || {}));
    } else {
      setSchema({});
      setParamsObj({});
    }
  };

  const handleParamChange = (key, val) => {
    setParamsObj((p) => ({ ...p, [key]: val }));
  };

  const addStep = () => {
    if (!name) {
      return alert("Chọn tên filter");
    }
    // add paramsObj (ensure plain object)
    setSteps((prev) => [...prev, { name, params: paramsObj || {} }]);
    setName("");
    setParamsObj({});
    setSchema({});
  };

  const removeStep = (i) =>
    setSteps((prev) => prev.filter((_, idx) => idx !== i));

  const renderParamField = (key, meta) => {
    const val = paramsObj?.[key];
    const t = (meta?.type || "string").toLowerCase();

    if (t === "enum") {
      const options = (meta.options || []).map((o) => ({ label: String(o), value: o }));
      return (
        <div className="param-row" key={key}>
          <div className="param-key">{key}</div>
          <div className="param-control">
            <Select
              options={options}
              value={val}
              onChange={(v) => handleParamChange(key, v)}
              style={{ minWidth: 140 }}
            />
          </div>
        </div>
      );
    }

    if (t === "int" || t === "float") {
      return (
        <div className="param-row" key={key}>
          <div className="param-key">{key}</div>
          <div className="param-control">
            <InputNumber
              value={val}
              min={meta.min}
              max={meta.max}
              step={meta.step ?? (t === "int" ? 1 : 0.1)}
              onChange={(v) => handleParamChange(key, v)}
              style={{ minWidth: 140 }}
            />
          </div>
        </div>
      );
    }

    if (t === "boolean") {
      return (
        <div className="param-row" key={key}>
          <div className="param-key">{key}</div>
          <div className="param-control">
            <Switch checked={!!val} onChange={(v) => handleParamChange(key, v)} />
          </div>
        </div>
      );
    }

    // default: string
    return (
      <div className="param-row" key={key}>
        <div className="param-key">{key}</div>
        <div className="param-control">
          <Input
            value={val}
            onChange={(e) => handleParamChange(key, e.target.value)}
            style={{ minWidth: 140 }}
          />
        </div>
      </div>
    );
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
                onClick={() => onSelectFilterFromList(f)}
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
          onChange={(e) => onNameChange(e.target.value)}
          className="filter-name"
        />

        <div className="json-editor-wrap">
          {/* Form-driven params editor */}
          {schema && Object.keys(schema).length ? (
            <div className="params-editor">
              <div className="params-editor-title">Chỉnh tham số</div>
              <div className="params-editor-body">
                {Object.entries(schema).map(([k, v]) => renderParamField(k, v))}
              </div>
            </div>
          ) : (
            <Text type="secondary">Không có tham số để chỉnh (hoặc filter không được chọn)</Text>
          )}
        </div>

        <Space>
          <Button type="primary" onClick={addStep} disabled={!name}>
            Thêm bước
          </Button>
          <Button danger onClick={() => setSteps([])}>
            Xoá hết
          </Button>
        </Space>
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
