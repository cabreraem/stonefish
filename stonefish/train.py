import os
import time
import argparse

from collections import deque

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

from stonefish.model import Model
from stonefish.dataset import ChessData, TTTData
from stonefish.eval import eval_model
from stonefish.rep import MoveToken
from stonefish.ttt import TTTBoardToken, TTTMoveToken


def main(log_file_path: str, load_model, load_opt):

    data = TTTData("data/ttt_train.csv")
    test_data = TTTData("data/ttt_test.csv")

    dataloader = DataLoader(data, batch_size=128, drop_last=True, shuffle=True)
    loss_fn = nn.CrossEntropyLoss()
    other_loss_fn = nn.CrossEntropyLoss(reduction='none')

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu") 
    model = Model(device, 256, TTTBoardToken, TTTMoveToken)
    model = model.to(model.device)
    if load_model:
        model.load_state_dict(torch.load(load_model))

    opt = optim.Adam(model.parameters(), lr=0.0001, betas=(0.9, 0.98), eps=1e-9)
    if load_opt:
        opt.load_state_dict(torch.load(load_opt))

    log_file = open(log_file_path, "w")

    losses = deque(maxlen=1000)

    for epoch in range(1000):
    
        acc, loss = eval_model(model, test_data, batch_size=256)
        print(f"({epoch - 1}) Acc: {round(acc, 2)} Test Loss: {loss}")
        log_file.write(f"TEST {epoch-1} {time.time()} {acc}\n")

        for (batch_idx, (s, a)) in enumerate(dataloader):
            s = s.to(device)
            labels = torch.flatten(a).to(device)
            
            opt.zero_grad()
            p = model(s, a)
            p = p.view(-1, 6)
            loss = loss_fn(p, labels)
            loss.backward()
            opt.step()

            loss = loss.item()
            losses.append(loss)

            if batch_idx > 0 and batch_idx % 100 == 0:
                print(f"({epoch}/{batch_idx}) Loss (Avg): {np.mean(losses)}")

            log_file.write(f"TRAIN {epoch} {batch_idx} {time.time()} {loss}\n")

        torch.save(model.state_dict(), f"model_{epoch}.pth")
        torch.save(opt.state_dict(), f"opt.pth")

    acc = eval_model(model, test_data)
    print(f"({epoch}) Acc: {round(acc, 2)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("log_file")
    parser.add_argument("--load_model")
    parser.add_argument("--load_opt")
    parser.add_argument("-o", default=False, action="store_true", help="Overwrite by default")
    args = parser.parse_args()
    
    go_ahead = args.o
    if not go_ahead and os.path.exists(args.log_file):
        res = input(f"File {args.log_file} exists. Overwrite? (Y/n) ")
        go_ahead = res == "" or res.lower() == "y"

    if not os.path.exists(args.log_file) or go_ahead:
        main(args.log_file, args.load_model, args.load_opt)
