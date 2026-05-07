import type { CalibrationPoint } from "@/types";

type VoidCallback = () => void;
type CalibrationPointsCallback = (points: CalibrationPoint[]) => void;

interface InkflowBridge {
  startCalibration?: () => Promise<void>;
  onCalibrationPoints?: (cb: CalibrationPointsCallback) => void;
  onCalibrationCancelled?: (cb: VoidCallback) => void;
  removeCalibrationListeners?: () => void;
  registerEscCancel?: () => void;
  unregisterEscCancel?: () => void;
  onEscPressed?: (cb: VoidCallback) => void;
  removeEscListeners?: () => void;
  openExportsFolder?: () => void;
}

declare global {
  interface Window {
    inkflow?: InkflowBridge;
  }
}

export {};
