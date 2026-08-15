import { Routes, Route } from "react-router-dom";
import Landing from "./pages/Landing";
import Dashboard from "./pages/Dashboard";
import DashboardLayout from "./components/DashboardLayout";
import {
  UploadSection,
  SummariesSection,
  ObligationsRisksSection,
  DeadlinesSection,
  ActionItemsSection,
} from "./pages/Dashboard";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/dashboard" element={<DashboardLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="upload" element={<UploadSection />} />
        <Route path="summaries" element={<SummariesSection />} />
        <Route path="obligations-risks" element={<ObligationsRisksSection />} />
        <Route path="deadlines" element={<DeadlinesSection />} />
        <Route path="action-items" element={<ActionItemsSection />} />
      </Route>
    </Routes>
  );
}
