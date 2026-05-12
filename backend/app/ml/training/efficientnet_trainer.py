"""
app/ml/training/efficientnet_trainer.py
=======================================
PyTorch training pipeline for EfficientNet on the external PlantVillage dataset.
"""

import copy
import logging
import time
from pathlib import Path
from typing import Dict, Any

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, random_split
    from torchvision import datasets, transforms, models
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from app.config.settings import settings
from app.ml.training.config import TrainingConfig
from app.ml._paths import MODELS_DIR

logger = logging.getLogger(__name__)

def train_efficientnet(config: TrainingConfig, job_id: str) -> Dict[str, Any]:
    """
    Executes the full training loop for EfficientNet.
    Includes data loading, augmentation, training, validation, and checkpointing.
    """
    if not HAS_TORCH:
        raise ImportError("PyTorch is not installed. Cannot train EfficientNet.")

    dataset_path = settings.get_dataset_path
    if not dataset_path or not Path(dataset_path).exists():
        raise ValueError(f"Dataset path not found: {dataset_path}")

    # Setup device
    if config.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(config.device)
        
    logger.info(f"🚀 Starting EfficientNet training on {device} (Job: {job_id})")

    # Data Transforms
    train_transforms = transforms.Compose([
        transforms.RandomResizedCrop(224),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    val_transforms = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    # Load Dataset
    full_dataset = datasets.ImageFolder(dataset_path, transform=train_transforms)
    num_classes = len(full_dataset.classes)
    config.num_classes = num_classes
    
    val_size = int(len(full_dataset) * config.val_split)
    train_size = len(full_dataset) - val_size
    train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size])
    
    # Override validation transforms
    val_dataset.dataset.transform = val_transforms

    train_loader = DataLoader(train_dataset, batch_size=config.batch_size, shuffle=True, num_workers=4)
    val_loader = DataLoader(val_dataset, batch_size=config.batch_size, shuffle=False, num_workers=4)

    # Initialize Model
    # Use efficientnet_b0 for speed during retraining
    model = models.efficientnet_b0(pretrained=True)
    num_ftrs = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_ftrs, num_classes)
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=config.learning_rate)
    scaler = torch.cuda.amp.GradScaler(enabled=config.mixed_precision and device.type == 'cuda')

    best_acc = 0.0
    best_model_wts = copy.deepcopy(model.state_dict())
    metrics_history = []

    # Training Loop
    start_time = time.time()
    for epoch in range(config.epochs):
        logger.info(f"Epoch {epoch+1}/{config.epochs}")
        
        # Train
        model.train()
        running_loss = 0.0
        running_corrects = 0
        
        for inputs, labels in train_loader:
            inputs = inputs.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            
            with torch.cuda.amp.autocast(enabled=config.mixed_precision and device.type == 'cuda'):
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                _, preds = torch.max(outputs, 1)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            running_loss += loss.item() * inputs.size(0)
            running_corrects += torch.sum(preds == labels.data)

        train_loss = running_loss / train_size
        train_acc = running_corrects.double() / train_size

        # Validation
        model.eval()
        val_loss = 0.0
        val_corrects = 0
        
        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs = inputs.to(device)
                labels = labels.to(device)

                outputs = model(inputs)
                loss = criterion(outputs, labels)
                _, preds = torch.max(outputs, 1)

                val_loss += loss.item() * inputs.size(0)
                val_corrects += torch.sum(preds == labels.data)

        val_loss = val_loss / val_size
        val_acc = val_corrects.double() / val_size

        logger.info(f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | Val Loss: {val_loss:.4f} Acc: {val_acc:.4f}")

        metrics_history.append({
            "epoch": epoch + 1,
            "train_loss": float(train_loss),
            "train_acc": float(train_acc),
            "val_loss": float(val_loss),
            "val_acc": float(val_acc)
        })

        if val_acc > best_acc:
            best_acc = val_acc
            best_model_wts = copy.deepcopy(model.state_dict())

    time_elapsed = time.time() - start_time
    logger.info(f"Training complete in {time_elapsed // 60:.0f}m {time_elapsed % 60:.0f}s")
    logger.info(f"Best val Acc: {best_acc:4f}")

    # Load best weights and save
    model.load_state_dict(best_model_wts)
    
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    save_path = MODELS_DIR / "efficientnet_model.pth"
    torch.save(model.state_dict(), str(save_path))

    return {
        "job_id": job_id,
        "model_name": "efficientnet",
        "best_accuracy": float(best_acc),
        "metrics_history": metrics_history,
        "checkpoint_path": str(save_path),
        "classes": full_dataset.classes
    }
