import { useState } from "react";
import "./App.css";
import ImagesList from "./components/ImagesList";
import FiltersPanel from "./components/FiltersPanel";
import RunPanel from "./components/RunPanel";
import OutputsList from "./components/OutputsList";

export default function App() {
  const [selectedImages, setSelectedImages] = useState([]);
  const [steps, setSteps] = useState([]);
  const [outsBumped, setOutsBumped] = useState([]);

  return (
    <main className="container">
      <header>
        <h1>Pipes & Filters – React Demo</h1>
        <small>Backend: http://127.0.0.1:8000</small>
      </header>

      <ImagesList selected={selectedImages} setSelected={setSelectedImages} />
      <FiltersPanel steps={steps} setSteps={setSteps} />
      <RunPanel
        selectedImages={selectedImages}
        steps={steps}
        onDone={(outs) => setOutsBumped(outs)}
      />
      <OutputsList externalOutputs={outsBumped} />
    </main>
  );
}
