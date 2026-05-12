import React, { useEffect, useState } from "react";
import { useStore } from "@/store";
import AppShell from "@/components/shared/AppShell";
import LandingScreen  from "@/components/landing/LandingScreen";
import EditorScreen   from "@/components/editor/EditorScreen";
import TrainerScreen  from "@/components/trainer/TrainerScreen";
import OneNoteScreen  from "@/components/onenote/OneNoteScreen";
import SettingsScreen from "@/components/settings/SettingsScreen";
import LicenseModal from "@/components/shared/LicenseModal";
import { checkHealth } from "@/utils/api";
import { checkLicense } from "@/utils/license";
import { Toaster } from "react-hot-toast";

export default function App() {
  const { screen, license, setLicense } = useStore();
  const [online, setOnline] = useState<boolean|null>(null);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    const check = () => {
      checkHealth().then(() => { setOnline(true); clearInterval(timer); }).catch(() => { setOnline(false); });
    };
    check();
    timer = setInterval(check, 2000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!license.key) return;
    checkLicense(license.key).then(res => {
      if (res.valid) {
        setLicense({ status: "valid", lastChecked: new Date().toISOString() });
      } else if (res.reason === "Offline") {
        // Only allow grace period if we are actually offline
        const last = license.lastChecked ? new Date(license.lastChecked) : new Date(0);
        const daysSinceLastCheck = (new Date().getTime() - last.getTime()) / (1000 * 3600 * 24);
        if (daysSinceLastCheck > 7) {
          setLicense({ status: "invalid" });
        }
      } else {
        // Server explicitly said license is invalid (Inactive, Expired, Not found, etc.)
        setLicense({ status: "invalid" });
      }
    });
  }, [license.key]);

  const render = () => {
    switch (screen) {
      case "landing":  return <LandingScreen/>;
      case "editor":   return <EditorScreen/>;
      case "trainer":  return <TrainerScreen/>;
      case "onenote":  return <OneNoteScreen/>;
      case "settings": return <SettingsScreen/>;
      default:         return <LandingScreen/>;
    }
  };

  return (
    <AppShell online={online}>
      <Toaster position="bottom-center" />
      <LicenseModal />
      {render()}
    </AppShell>
  );
}
