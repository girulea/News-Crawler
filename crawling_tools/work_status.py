from enum import Enum


class WorkStatus(Enum):
	ProcessingInQueue = 'ProcessingInQueue'
	UnderProcessing = 'UnderProcessing'
	Processed = 'Processed'