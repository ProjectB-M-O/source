"""
Converte il training checkpoint di RVC nel formato inference atteso da rvc-python.

Il training checkpoint ha: model, iteration, optimizer, learning_rate
Il formato inference richiede: weight, config, f0, version
"""
import os
import torch

SRC = os.path.join(os.path.dirname(__file__), "../export/bmo_rvc_model/bmo.pth")
DST = os.path.join(os.path.dirname(__file__), "../export/bmo_rvc_model/bmo_infer.pth")

cpt = torch.load(SRC, map_location="cpu")
print("Chiavi originali:", list(cpt.keys()))
print("Iteration:", cpt.get("iteration"))

# Verifica architettura dal checkpoint
sd = cpt["model"]
emb_phone_shape = sd["enc_p.emb_phone.weight"].shape  # [hidden, feature_dim]
emb_g_shape = sd["emb_g.weight"].shape                # [n_spk, gin_channels]
print(f"enc_p.emb_phone: {emb_phone_shape}  feature_dim={emb_phone_shape[1]} (768=v2, 256=v1)")
print(f"emb_g:           {emb_g_shape}  -> spk_embed_dim={emb_g_shape[0]}, gin_channels={emb_g_shape[1]}")

version = "v2" if emb_phone_shape[1] == 768 else "v1"
spk_embed_dim = emb_g_shape[0]
gin_channels = emb_g_shape[1]

# Config 48k v2 (da configs/v2/48k.json + training defaults)
# Ordine: spec_channels, segment_size, inter_channels, hidden_channels,
#         filter_channels, n_heads, n_layers, kernel_size, p_dropout,
#         resblock, resblock_kernel_sizes, resblock_dilation_sizes,
#         upsample_rates, upsample_initial_channel, upsample_kernel_sizes,
#         spk_embed_dim, gin_channels, sr
config = [
    1025,               # spec_channels  (filter_length/2+1 = 2048/2+1)
    32,                 # segment_size   (12800/400 hop_length, 40k config)
    192,                # inter_channels
    192,                # hidden_channels
    768,                # filter_channels
    2,                  # n_heads
    6,                  # n_layers
    3,                  # kernel_size
    0,                  # p_dropout
    "1",                # resblock
    [3, 7, 11],         # resblock_kernel_sizes
    [[1, 3, 5], [1, 3, 5], [1, 3, 5]],  # resblock_dilation_sizes
    [10, 10, 2, 2],     # upsample_rates  (40k: total=400 hop)
    512,                # upsample_initial_channel
    [16, 16, 4, 4],     # upsample_kernel_sizes (da dec.ups weight shapes)
    spk_embed_dim,      # spk_embed_dim (da emb_g)
    gin_channels,       # gin_channels  (da emb_g)
    40000,              # sr
]

infer_cpt = {
    "weight": sd,
    "config": config,
    "f0": 1,         # NSF / F0 conditioning abilitato
    "version": version,
    "info": f"bmo fine-tuned {cpt.get('iteration', '?')}epoch",
}

torch.save(infer_cpt, DST)
print(f"\nSalvato: {DST}")
print(f"Versione: {version}, sr=48000, f0=1, spk={spk_embed_dim}")
