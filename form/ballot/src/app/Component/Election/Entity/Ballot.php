<?php

namespace App\Component\Election\Entity;

use App\Component\Election\Setting;
use App\Component\Election\Guid;

class Ballot {

    private Setting\Entity\Setting $_settings;
    private Guid\Entity\Guid $_guid;
    private int $_guidsCount;

    public function __construct(Setting\Entity\Setting $settings, Guid\Entity\Guid $guid, int $guidsCount) {
        $this->_settings = $settings;
        $this->_guid = $guid;
        $this->_guidsCount = $guidsCount;
    }

    public function getSettings(): Setting\Entity\Setting {
        return $this->_settings;
    }

    public function getGuid(): Guid\Entity\Guid {
        return $this->_guid;
    }

    public function getGuidsCount(): int {
        return $this->_guidsCount;
    }
}
