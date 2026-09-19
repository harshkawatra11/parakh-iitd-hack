import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Tooltip,
  Legend
);

export const INK = "#14130F";
export const INK_3 = "#7A766C";
export const SEAL = "#B3122B";
export const OLIVE = "#6B6A4E";
export const VERDIGRIS = "#2F6B5E";
export const RULE = "rgba(20,19,15,0.08)";

export const baseOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: "#14130F",
      titleFont: { family: "JetBrains Mono", size: 11 },
      bodyFont: { family: "JetBrains Mono", size: 11 },
      padding: 8,
      cornerRadius: 2,
      displayColors: false,
    },
  },
  scales: {
    x: {
      grid: { color: RULE, drawTicks: false },
      ticks: { font: { family: "JetBrains Mono", size: 10 }, color: INK_3 },
      border: { color: RULE },
    },
    y: {
      grid: { color: RULE, drawTicks: false },
      ticks: { font: { family: "JetBrains Mono", size: 10 }, color: INK_3 },
      border: { display: false },
    },
  },
};
