import skia


def parse_blend_mode(blend_mode: str | None) -> skia.BlendMode:
    """Convert blend mode string to Skia blend mode"""
    # CSS mix-blend-mode
    if blend_mode == "multiply":
        return skia.BlendMode.kMultiply
    if blend_mode == "difference":
        return skia.BlendMode.kDifference

    if blend_mode == "destination-in":
        return skia.BlendMode.kDstIn
    return skia.BlendMode.kSrcOver
