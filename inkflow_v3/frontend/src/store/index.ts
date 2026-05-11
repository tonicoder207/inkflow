import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { AppScreen, HandwritingProfile, ProfileSummary, RenderResult, PaperStyle, CalibrationProfile, WriteStatus } from "@/types";

interface LicenseState {
  key: string | null;
  status: "valid" | "invalid" | "expired" | "none";
  expiresAt: string | null;
  lastChecked: string | null;
  licenseType: string | null;
}

interface Store {
  screen: AppScreen; setScreen: (s:AppScreen) => void;
  profiles: ProfileSummary[]; setProfiles: (p:ProfileSummary[]) => void;
  activeProfile: HandwritingProfile|null; setActiveProfile: (p:HandwritingProfile|null) => void;
  editorText: string; setEditorText: (t:string) => void;
  paperStyle: PaperStyle; setPaperStyle: (p:Partial<PaperStyle>) => void;
  renderResult: RenderResult|null; setRenderResult: (r:RenderResult|null) => void;
  isRendering: boolean; setIsRendering: (b:boolean) => void;
  trainerProfileId: string|null; setTrainerProfileId: (id:string|null) => void;
  calibrations: CalibrationProfile[]; setCalibrations: (c:CalibrationProfile[]) => void;
  activeCalibration: CalibrationProfile|null; setActiveCalibration: (c:CalibrationProfile|null) => void;
  writeStatus: WriteStatus|null; setWriteStatus: (s:WriteStatus|null) => void;
  onenoteText: string; setOnenoteText: (t:string) => void;
  license: LicenseState;
  setLicense: (l: Partial<LicenseState>) => void;
}

const DEFAULT_PAPER: PaperStyle = {
  type:"lined", color:"#fdf6e3", line_color:"#c8d6e5",
  margin_left:80, margin_top:80, width:2480, height:3508,
};

export const useStore = create<Store>()(
  persist(
    (set) => ({
      screen: "landing",          setScreen:          (screen)          => set({screen}),
      profiles: [],               setProfiles:         (profiles)        => set({profiles}),
      activeProfile: null,        setActiveProfile:    (activeProfile)   => set({activeProfile}),
      editorText: "",             setEditorText:       (editorText)      => set({editorText}),
      paperStyle: DEFAULT_PAPER,  setPaperStyle:       (p)               => set(s => ({paperStyle:{...s.paperStyle,...p}})),
      renderResult: null,         setRenderResult:     (renderResult)    => set({renderResult}),
      isRendering: false,         setIsRendering:      (isRendering)     => set({isRendering}),
      trainerProfileId: null,     setTrainerProfileId: (trainerProfileId)=> set({trainerProfileId}),
      calibrations: [],           setCalibrations:     (calibrations)    => set({calibrations}),
      activeCalibration: null,    setActiveCalibration:(activeCalibration)=> set({activeCalibration}),
      writeStatus: null,          setWriteStatus:      (writeStatus)     => set({writeStatus}),
      onenoteText: "",            setOnenoteText:      (onenoteText)     => set({onenoteText}),
      license: { key: null, status: "none", expiresAt: null, lastChecked: null, licenseType: null },
      setLicense: (l) => set((s) => ({ license: { ...s.license, ...l } })),
    }),
    {
      name: "inkflow-storage",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ license: state.license }),
    }
  )
);
