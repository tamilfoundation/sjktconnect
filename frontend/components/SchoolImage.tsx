"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { SchoolImageData } from "@/lib/types";

// Lazy: lightbox is heavy and only loads when a user clicks. Also
// avoids SSR issues — the lib touches `window` at import time.
const PhotoLightbox = dynamic(() => import("./PhotoLightbox"), { ssr: false });

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
    photoList = [
      {
        id: 0,
        image_url: imageUrl,
        source: "PLACES" as const,
        position: 0,
        is_primary: true,
        attribution: "",
        caption: "",
      },
    ];
  } else {
    photoList = [];
  }

  const [activeIndex, setActiveIndex] = useState(0);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [lightboxIndex, setLightboxIndex] = useState(0);

  const openLightbox = (i: number) => {
    setLightboxIndex(i);
    setLightboxOpen(true);
  };

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
    <>
      <div className="relative w-full h-64 sm:h-80 lg:h-[400px] rounded-xl overflow-hidden shadow-sm bg-gray-200 group">
        {/* Main image — clickable to open lightbox */}
        <button
          onClick={() => openLightbox(activeIndex)}
          className="block w-full h-full focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
          aria-label={`Open ${schoolName} photo viewer`}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={active.image_url}
            alt={active.caption || schoolName}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        </button>

        {/* Caption overlay (bottom centre) */}
        {active.caption && (
          <div className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 text-xs text-white bg-black/55 px-3 py-1.5 rounded backdrop-blur-sm max-w-[80%] text-center truncate">
            {active.caption}
          </div>
        )}

        {/* "View all N photos" overlay — top-right when there are more than 5 */}
        {photoList.length > 5 && (
          <button
            onClick={() => openLightbox(0)}
            className="absolute top-3 right-3 text-xs text-white bg-black/60 hover:bg-black/80 px-3 py-1.5 rounded-full backdrop-blur-sm font-medium transition-colors"
          >
            View all {photoList.length} photos
          </button>
        )}

        {/* Attribution (bottom-right) */}
        {active.attribution && (
          <div className="pointer-events-none absolute bottom-3 right-3 text-[10px] text-white/80 bg-black/40 px-2 py-1 rounded backdrop-blur-sm">
            {t("photoCredit")} {active.attribution.replace(/<[^>]*>/g, "")}
          </div>
        )}

        {/* Thumbnail strip overlaid at bottom-left */}
        {photoList.length > 1 && (
          <div className="absolute bottom-3 left-3 flex gap-2">
            {photoList.slice(0, 4).map((img, i) => (
              <button
                key={img.id || i}
                onClick={(e) => {
                  e.stopPropagation();
                  // single-click: switch the hero; double-click handled by
                  // separate lightbox open via the hero button.
                  setActiveIndex(i);
                }}
                onDoubleClick={() => openLightbox(i)}
                className={`w-20 h-14 rounded-lg overflow-hidden flex-shrink-0 transition-all ${
                  i === activeIndex
                    ? "border-2 border-primary-500 opacity-100"
                    : "border border-white/50 opacity-70 hover:opacity-100"
                }`}
                title="Click to set as hero · Double-click to open viewer"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={img.image_url}
                  alt={img.caption || `${schoolName} photo ${i + 1}`}
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
              </button>
            ))}
          </div>
        )}
      </div>

      {lightboxOpen && (
        <PhotoLightbox
          open={lightboxOpen}
          index={lightboxIndex}
          onClose={() => setLightboxOpen(false)}
          images={photoList}
          schoolName={schoolName}
        />
      )}
    </>
  );
}
