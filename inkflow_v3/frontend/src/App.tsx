import React, { useEffect, useState } from "react";
import { useStore } from "@/store";
import AppShell from "@/components/shared/AppShell";
import LandingScreen  from "@/components/landing/LandingScreen";
import EditorScreen   from "@/components/editor/EditorScreen";
import TrainerScreen  from "@/components/trainer/TrainerScreen";
import OneNoteScreen  from "@/components/onenote/OneNoteScreen";
import SettingsScreen from "@/components/settings/SettingsScreen";
import { checkHealth } from "@/utils/api";

export default function App() {
  const { screen } = useStore();
  const [online, setOnline] = useState<boolean|null>(null);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    
    const check = () => {
      checkHealth()
        .then(() => {
          setOnline(true);
          clearInterval(timer);
        })
        .catch(() => {
          setOnline(false);
        });
    };

    check();
    timer = setInterval(check, 2000);
    return () => clearInterval(timer);
  }, []);

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
      {render()}
    </AppShell>
  );
}
