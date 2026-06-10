import { Route, Routes } from "react-router-dom";
import MainLayout from "./layouts/MainLayout";
import Home from "./pages/Home";
import Matches from "./pages/Matches";
import Predictions from "./pages/Predictions";
import Ranking from "./pages/Ranking";
import Stats from "./pages/Stats";
import Participant from "./pages/Participant";
import Admin from "./pages/Admin";
import NotFound from "./pages/NotFound";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Home />} />
        <Route path="partidos" element={<Matches />} />
        <Route path="predicciones" element={<Predictions />} />
        <Route path="ranking" element={<Ranking />} />
        <Route path="estadisticas" element={<Stats />} />
        <Route path="participante" element={<Participant />} />
        <Route path="admin" element={<Admin />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
