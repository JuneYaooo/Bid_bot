from abc import ABC, abstractmethod

class BaseClient(ABC):
    @abstractmethod
    def get_completion(self, messages):
        pass

    @abstractmethod
    def extract_from_image(self, image_path):
        pass
