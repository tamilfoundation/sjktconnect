"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { SchoolImageData } from "@/lib/types";

interface Props {
  images?: SchoolImageData[];
  schoolName: string;
  imageUrl?: string | null;
}

export default function SchoolPhotoGallery({
  images,
  schoolName,
  imageUrl,
}: Props) {
  const t = useTranslations("parliamentWatch");

  let photoList: SchoolImageData[];
  if (images && images.length > 0) {
    photoList = images;
  } else if (imageUrl) {
    photoList = [{ image_url: imageUrl, source: "PLACES" as const, is_primary: true, attribution: "" }];
  } else {
    photoList = [];
  }

  const [activeIndex, setActiveIndex] = useState(0);

  if (photoList.length === 0) {
    return (
      <div className="bg-gray-100 rounded-xl h-64 sm:h-80 lg:h-[400px] flex items-center justify-center">
        <p className="text-gray-400 text-sm">
          {t("noPhoto")}
        </p>
      </div>
    );
  }

  const active = photoList[activeIndex];

  return (
    <div className="relative w-full h-64 sm:h-80 lg:h-[400px] rounded-xl overflow-hidden shadow-sm bg-gray-200 group">
      {/* Main image */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={active.image_url}
        alt={schoolName}
        className="w-full h-full object-cover"
        loading="lazy"
      />

      {/* Attribution overlay */}
      {active.attribution && (
        <div className="absolute bottom-2 right-3 text-[10px] text-white/80 bg-black/40 px-2 py-1 rounded backdrop-blur-sm">
          {t("photoCredit")} {active.attribution.replace(/<[^>]*>/g, "")}
        </div>
      )}

      {/* Thumbnail strip overlaid at bottom-left */}
      {photoList.length > 1 && (
        <div className="absolute bottom-3 left-3 flex gap-2">
          {photoList.map((img, i) => (
            // eslint-disable-next-line @next/next/no-img-element
            <button
              key={i}
              onClick={() => setActiveIndex(i)}
              className={`w-20 h-14 rounded-lg overflow-hidden flex-shrink-0 transition-all ${
                i === activeIndex
                  ? "border-2 border-primary-500 opacity-100"
                  : "border border-white/50 opacity-70 hover:opacity-100"
              }`}
            >
              <img
                src={img.image_url}
                alt={`${schoolName} photo ${i + 1}`}
                className="w-full h-full object-cover"
                loading="lazy"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
