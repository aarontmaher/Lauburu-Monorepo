import React, { useState } from 'react';

export interface RashguardProductProps {
  initialPriceAud?: number;
  wholesaleFloorAud?: number;
  inStock?: boolean;
}

export const RashguardProductCard: React.FC<RashguardProductProps> = ({
  initialPriceAud = 65.0,
  wholesaleFloorAud = 48.0,
  inStock = true,
}) => {
  const [selectedSize, setSelectedSize] = useState<'S' | 'M' | 'L' | 'XL'>('M');
  const [hasCustomPatch, setHasCustomPatch] = useState(false);
  const [isOrdering, setIsOrdering] = useState(false);

  const calculateTotal = () => {
    const patchPrice = hasCustomPatch ? 6.0 : 0.0;
    return (initialPriceAud + patchPrice).toFixed(2);
  };

  const handleCheckout = () => {
    setIsOrdering(true);
    // Trigger Shopify Storefront API cart lines add mutation
    console.log(`[Stitch 2.0] Adding Rashguard to cart: Size=${selectedSize}, CustomPatch=${hasCustomPatch}`);
    setTimeout(() => setIsOrdering(false), 800);
  };

  return (
    <div className="max-w-md w-full rounded-2xl bg-zinc-950/80 border border-white/10 backdrop-blur-xl shadow-2xl overflow-hidden p-6 text-white font-sans">
      <div className="flex justify-between items-center mb-3">
        <span className="text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 border border-red-500/30">
          Absolute MMA 1:1 Cut
        </span>
        <span className="text-xs text-zinc-400 font-mono">250 GSM Poly-Spandex</span>
      </div>

      <h2 className="text-2xl font-black tracking-tight text-white mb-1">
        Lauburu Stealth Rashguard
      </h2>
      <p className="text-xs text-zinc-400 mb-4 leading-relaxed">
        Reconstructed pattern with 25mm silicone waistband and reinforced flatlock stitching.
      </p>

      {/* Pricing Header */}
      <div className="flex items-baseline space-x-2 mb-4">
        <span className="text-3xl font-black text-white">${calculateTotal()}</span>
        <span className="text-xs text-zinc-400 line-through">$85.00 AUD</span>
        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400">
          Pre-Order
        </span>
      </div>

      {/* Size Selection */}
      <div className="mb-4">
        <label className="block text-xs font-bold uppercase tracking-wider text-zinc-300 mb-2">
          Select Fit
        </label>
        <div className="grid grid-cols-4 gap-2">
          {(['S', 'M', 'L', 'XL'] as const).map((size) => (
            <button
              key={size}
              type="button"
              onClick={() => setSelectedSize(size)}
              className={`py-2 rounded-lg font-bold text-xs transition-all ${
                selectedSize === size
                  ? 'border-2 border-red-500 bg-red-500/20 text-white shadow-lg shadow-red-500/20'
                  : 'border border-white/10 bg-zinc-900/60 text-zinc-400 hover:text-white hover:border-zinc-500'
              }`}
            >
              {size}
            </button>
          ))}
        </div>
      </div>

      {/* Academy Customization Toggle */}
      <label className="flex items-center space-x-3 p-3 rounded-lg bg-zinc-900/40 border border-white/5 mb-5 cursor-pointer">
        <input
          type="checkbox"
          checked={hasCustomPatch}
          onChange={(e) => setHasCustomPatch(e.target.checked)}
          className="rounded border-zinc-700 text-red-600 focus:ring-red-500 bg-zinc-950"
        />
        <span className="text-xs text-zinc-300">
          <strong className="text-white block">Custom Academy Club Sublimation (+$6.00)</strong>
          Tone-matched vector graphics directly infused into fabric.
        </span>
      </label>

      {/* CTA Button */}
      <button
        type="button"
        disabled={isOrdering}
        onClick={handleCheckout}
        className="w-full py-3.5 px-4 rounded-xl bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 font-extrabold text-sm tracking-wide uppercase transition-all shadow-lg shadow-red-600/30 disabled:opacity-50"
      >
        {isOrdering ? 'Securing Pre-Order...' : 'Claim Sample Reservation'}
      </button>

      <div className="mt-3 text-center text-[10px] text-zinc-400 font-mono">
        Wholesale B2B Tier: $48 AUD (20-49) | $42 AUD (50+)
      </div>
    </div>
  );
};

export default RashguardProductCard;
