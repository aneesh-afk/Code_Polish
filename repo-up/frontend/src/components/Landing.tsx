import React, { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileArchive,
  GitBranch,
  FileCode2,
  ChevronRight,
  Lock,
} from "lucide-react";

interface LandingProps {
  onAnalyze: (file?: File) => void;
}

export const Landing: React.FC<LandingProps> = ({ onAnalyze }) => {
  const [activeTab, setActiveTab] = useState<"zip" | "github" | "paste">("zip");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const isAnalyzeEnabled = activeTab === "zip" && selectedFile !== null;

  const handleFileSelect = (f: File | null | undefined) => {
    setFileError(null);
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".zip")) {
      setFileError(
        "Only .zip files are supported. Please select a valid ZIP archive.",
      );
      setSelectedFile(null);
      return;
    }
    setSelectedFile(f);
  };

  const handleDrop = useCallback((e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    handleFileSelect(e.dataTransfer.files?.[0]);
  }, []);

  const tabs = [
    {
      id: "zip",
      icon: FileArchive,
      label: "Upload ZIP",
      sub: ".zip · 50 MB",
      disabled: false,
    },
    {
      id: "github",
      icon: GitBranch,
      label: "GitHub repo",
      sub: "Coming soon",
      disabled: true,
    },
    {
      id: "paste",
      icon: FileCode2,
      label: "Paste code",
      sub: "Coming soon",
      disabled: true,
    },
  ] as const;

  return (
    <div className="w-full max-w-7xl mx-auto px-4 lg:px-8 py-12 flex flex-col lg:flex-row items-center gap-16 relative z-10">
      {/* Left Column */}
      <div className="flex-1 w-full flex flex-col items-start">
        {/* Unified Glass Text Panel */}
        <div className="hover-glass rounded-2xl p-8 md:p-10 mb-8 w-full max-w-[680px]">
          <h1 className="text-5xl lg:text-6xl font-bold mb-6 tracking-tight text-white font-display leading-tight">
            Repo-Up
          </h1>
          <p className="text-base lg:text-lg text-secondary-dark max-w-[480px] leading-[1.6]">
            Code doesn&rsquo;t fail in isolation — it fails in connections.
            Repo-Up maps every file, every call, every dependency, and tells you
            exactly where the structure gives way.
          </p>
        </div>
      </div>

      {/* Right Column: Upload Card */}
      <motion.div
        initial={{ opacity: 0, x: 40 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8, ease: "easeOut", delay: 0.1 }}
        className="w-full max-w-md lg:w-[480px] shrink-0"
      >
        <div className="relative group/upload rounded-2xl p-[1px]">
          {/* Gradient border wrapper */}
          <div className="absolute inset-0 bg-gradient-to-br from-[#6D5EF0]/40 to-blue-500/40 opacity-70 rounded-2xl group-hover/upload:from-[#6D5EF0] group-hover/upload:to-blue-500 group-hover/upload:opacity-100 transition-all duration-500" />

          <div className="bg-[#0b0c10]/55 backdrop-blur-[16px] rounded-2xl p-6 relative z-10 h-full w-full group-hover/upload:shadow-[0_8px_32px_rgba(109,94,240,0.25)] transition-shadow duration-300">
            {/* Tabs */}
            <div className="flex gap-2 mb-8">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  disabled={tab.disabled}
                  onClick={() => !tab.disabled && setActiveTab(tab.id as "zip")}
                  title={tab.disabled ? "Coming soon" : undefined}
                  aria-disabled={tab.disabled}
                  className={`flex-1 p-3 rounded-xl border border-transparent text-left transition-all relative overflow-hidden ${
                    activeTab === tab.id && !tab.disabled
                      ? "bg-gradient-to-br from-[#6D5EF0]/20 to-blue-500/20 shadow-[0_0_15px_rgba(109,94,240,0.2)]"
                      : "bg-white/5"
                  } ${tab.disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer hover:bg-white/10 hover:border-white/10"}`}
                >
                  <tab.icon
                    size={16}
                    className={`mb-2 ${activeTab === tab.id && !tab.disabled ? "text-[#6D5EF0]" : "text-secondary-dark"}`}
                  />
                  <div
                    className={`text-sm font-semibold mb-1 ${activeTab === tab.id && !tab.disabled ? "text-primary-dark" : "text-secondary-dark"}`}
                  >
                    {tab.label}
                  </div>
                  <div className="text-[10px] text-secondary-dark font-mono">
                    {tab.sub}
                  </div>
                </button>
              ))}
            </div>

            {/* Content Area */}
            <div className="bg-black/20 border border-white/5 rounded-xl p-5 mb-4">
              <AnimatePresence mode="wait">
                {activeTab === "zip" && (
                  <motion.div
                    key="zip"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="flex flex-col items-center justify-center text-center relative"
                  >
                    <label
                      className={`w-full flex flex-col items-center justify-center py-6 border-2 border-dashed rounded-lg cursor-pointer relative group/drop z-0 transition-all ${
                        isDragOver
                          ? "border-[#6D5EF0] bg-[#6D5EF0]/10"
                          : "border-[#6D5EF0]/40 hover:border-transparent"
                      }`}
                      onDragOver={(e) => {
                        e.preventDefault();
                        setIsDragOver(true);
                      }}
                      onDragLeave={() => setIsDragOver(false)}
                      onDrop={handleDrop}
                    >
                      {/* Gradient border on hover */}
                      <div className="absolute -inset-[2px] rounded-lg bg-gradient-to-br from-[#6D5EF0] to-blue-500 opacity-0 group-hover/drop:opacity-100 -z-10 transition-opacity" />
                      <div className="absolute inset-0 rounded-lg bg-[#0b0c10] opacity-0 group-hover/drop:opacity-100 -z-10 transition-opacity" />
                      <div className="absolute inset-0 rounded-lg bg-gradient-to-br from-[#6D5EF0]/15 to-blue-500/15 opacity-0 group-hover/drop:opacity-100 -z-10 transition-opacity" />

                      <FileArchive
                        size={24}
                        className={`mb-2 relative z-10 ${selectedFile ? "text-[#6D5EF0]" : "text-secondary-dark"}`}
                      />
                      <div className="text-sm font-medium text-primary-dark relative z-10">
                        {selectedFile
                          ? selectedFile.name
                          : "Click to browse or drag & drop"}
                      </div>
                      <div className="text-xs text-secondary-dark mt-1 relative z-10">
                        .zip files only · max 50 MB
                      </div>
                      <input
                        type="file"
                        accept=".zip"
                        className="hidden"
                        onChange={(e) => handleFileSelect(e.target.files?.[0])}
                      />
                    </label>
                    {/* File validation error */}
                    {fileError && (
                      <p className="mt-3 text-xs text-[#EF4444] text-center">
                        {fileError}
                      </p>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Action Button */}
            <button
              onClick={() => onAnalyze(selectedFile ?? undefined)}
              disabled={!isAnalyzeEnabled}
              className={`w-full py-4 rounded-xl font-semibold text-sm transition-all flex items-center justify-center gap-2 ${
                isAnalyzeEnabled
                  ? "bg-[#6D5EF0] text-white hover:bg-[#6D5EF0]/95 shadow-[0_0_20px_rgba(109,94,240,0.3)] hover:shadow-[0_0_30px_rgba(109,94,240,0.5)]"
                  : "bg-[#2A2E37]/50 text-secondary-dark cursor-not-allowed border border-white/5"
              }`}
            >
              {isAnalyzeEnabled
                ? "Analyse Project"
                : "Select a ZIP file to continue"}
              {isAnalyzeEnabled && <ChevronRight size={16} />}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
};
