import torch
import torch.nn as nn

import reBert.layerUtil as layerUtil

class EmbeddingLayer(nn.Module):
    def __init__(self, config):
        super(EmbeddingLayer, self).__init__()
        self.config = config
        self.position_emb = nn.Embedding(config['max_len'], config['d_model'])
        self.seg_emb = nn.Embedding(2, config['d_model'])
        
        self.norm = nn.LayerNorm(config['d_model'])
        
    def forward(self, x, segment_mask):
        pos = self.__to_position_mask(x)
        
        embedding = x + self.position_emb(pos) + self.seg_emb(segment_mask)
        return self.norm(embedding)
        
    def __to_position_mask(self, x):
        batch_size, seq_len, _ = x.shape
        pos = torch.torch.arange(seq_len, dtype=torch.long)
        pos = pos.unsqueeze(0).repeat(batch_size, 1)
        pos = pos.to(self.config['device'])
        return pos

class MultiHeadAttention(nn.Module):
    def __init__(self, config):
        super(MultiHeadAttention, self).__init__()
        self.config = config
        
        self.W_Q = nn.Linear(config['d_model'], config['d_model'] * config['n_heads'])
        self.W_K = nn.Linear(config['d_model'], config['d_model'] * config['n_heads'])
        self.W_V = nn.Linear(config['d_model'], config['d_model'] * config['n_heads'])
        
        self.W_out = nn.Linear(config['d_model'] * config['n_heads'], config['d_model'])
        
    def forward(self, Q, K, V, attention_pad_mask):
        batch_size = Q.size(0)
        
        #Batch x n_head x seq_len x d_model
        q_s = self.W_Q(Q).view(batch_size, -1, self.config['n_heads'], self.config['d_model']).transpose(1, 2)
        k_s = self.W_K(K).view(batch_size, -1, self.config['n_heads'], self.config['d_model']).transpose(1, 2)
        v_s = self.W_V(V).view(batch_size, -1, self.config['n_heads'], self.config['d_model']).transpose(1, 2)
        
        #Batch x n_head x seq_len x seq_len
        atten_pad_mask = attention_pad_mask.unsqueeze(1).repeat(1, self.config['n_heads'], 1, 1)

        context = layerUtil.get_scaledDotProductAttention(q_s, k_s, v_s, atten_pad_mask)
        context = context.transpose(1, 2).contiguous().view(batch_size, -1, self.config['n_heads'] * self.config['d_model'])
        #Batch x seq_len x n_head * d_model
        
        output = self.W_out(context)
        return output