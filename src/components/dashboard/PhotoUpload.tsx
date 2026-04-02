import { useState, useRef } from "react";
import { Upload, Camera, Leaf } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useNavigate } from "react-router-dom";

export function PhotoUpload() {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [plantType, setPlantType] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === "dragenter" || e.type === "dragover");
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) setSelectedFile(e.dataTransfer.files[0]);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) setSelectedFile(e.target.files[0]);
  };

  const handleAnalyze = () => {
    navigate("/analysis/1");
  };

  return (
    <Card className="animate-fade-in">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Camera className="h-5 w-5 text-primary" />
          Hızlı Hastalık Analizi
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Drop zone */}
        <div
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileRef.current?.click()}
          className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-colors ${
            dragActive ? "border-primary bg-accent" : "border-border hover:border-primary/50 hover:bg-accent/50"
          }`}
        >
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleFileChange} />
          {selectedFile ? (
            <div className="text-center">
              <Leaf className="mx-auto mb-2 h-10 w-10 text-success" />
              <p className="text-sm font-medium text-foreground">{selectedFile.name}</p>
              <p className="text-xs text-muted-foreground">Dosya hazır</p>
            </div>
          ) : (
            <>
              <Upload className="mb-3 h-10 w-10 text-muted-foreground" />
              <p className="text-sm font-medium text-foreground">Fotoğraf yükleyin veya sürükleyin</p>
              <p className="text-xs text-muted-foreground">PNG, JPG, WEBP (max 10MB)</p>
            </>
          )}
        </div>

        {/* Plant type */}
        <Select value={plantType} onValueChange={setPlantType}>
          <SelectTrigger>
            <SelectValue placeholder="Bitki türü seçin" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="tomato">🍅 Domates</SelectItem>
            <SelectItem value="potato">🥔 Patates</SelectItem>
            <SelectItem value="grape">🍇 Üzüm</SelectItem>
            <SelectItem value="apple">🍎 Elma</SelectItem>
            <SelectItem value="corn">🌽 Mısır</SelectItem>
            <SelectItem value="wheat">🌾 Buğday</SelectItem>
            <SelectItem value="other">🌿 Diğer</SelectItem>
          </SelectContent>
        </Select>

        <Button className="w-full" size="lg" disabled={!selectedFile} onClick={handleAnalyze}>
          <Leaf className="mr-2 h-4 w-4" />
          Analiz Et
        </Button>
      </CardContent>
    </Card>
  );
}
