"""Check both split paths against a single causal SDPA pass for the entire sequence."""
import torch
import torch.nn.functional as F
from split_control import AuditAttention, DECODE, HEADS, WIDTH, matched_paths

torch.set_num_threads(1)
with torch.inference_mode():
    errors=[]
    for batch in (1,4):
        for prefix in (16,256):
            torch.manual_seed(42)
            model=AuditAttention(WIDTH,HEADS).double().eval()
            x=torch.randn(batch,prefix+DECODE,WIDTH,dtype=torch.float64)
            q,k,v=model.projections(x)
            joined=F.scaled_dot_product_attention(q,k,v,is_causal=True,dropout_p=0.0)
            dense=model.out(joined.transpose(1,2).reshape(batch,prefix+DECODE,WIDTH))
            for name,calc in matched_paths(model,x,prefix).items():
                value=calc()
                torch.testing.assert_close(value,dense[:,prefix:],rtol=1e-11,atol=1e-11)
                errors.append((value-dense[:,prefix:]).abs().max().item())
    print(f'{len(errors)} float64 comparisons passed. Largest absolute difference: {max(errors):.4g}.')
